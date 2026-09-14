"""Executable private Checkout → signed receipt → report → browser delivery.

No account/endpoint creation, email sender or live-payment enablement is implied.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import stat
import time
from pathlib import Path
from urllib.parse import urlsplit
from wsgiref.simple_server import WSGIRequestHandler, make_server

from report_fetch import FetchError, fetch_public_html
from stripe_checkout import MAX_BODY, ROOT, PaymentError, StripeCheckout, StripeConfig, create_wsgi_app

CANONICAL = "https://priyanshchordia.com"
ORDER = re.compile(r"ord_[a-f0-9]{32}")


def load_protected_environment(path: Path):
    """Load an owner-only JSON environment map without printing any values."""
    path = path.expanduser().absolute()
    if path.resolve().is_relative_to(ROOT) or path.is_symlink():
        raise PaymentError("Runtime configuration must be a private file outside the repository.")
    if os.name != "posix":
        raise PaymentError("Use the protected process environment on Windows; apply owner-only ACLs first.")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PaymentError("Runtime configuration must be an owner-only regular file.")
        if info.st_size > 32768:
            raise PaymentError("Runtime configuration exceeds the size limit.")
        values = json.load(stream)
    if not isinstance(values, dict) or not values or any(not isinstance(k, str) or not k.startswith("COMMERCELINT_")
            or not isinstance(v, str) for k, v in values.items()):
        raise PaymentError("Runtime configuration must contain only CommerceLint string settings.")
    os.environ.update(values)


class CheckoutRuntime:
    def __init__(self, checkout: StripeCheckout, *, delivery_key: str, origin: str,
                 fetcher=fetch_public_html, clock=time.time):
        parsed = urlsplit(origin)
        local = parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and checkout.config.mode == "test"
        if (not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", delivery_key) or not parsed.hostname
                or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                or not (local or parsed.scheme == "https")):
            raise PaymentError("Set a strong private delivery key and an HTTPS runtime origin (loopback allowed in test mode).")
        self.checkout, self.origin, self.fetcher, self.clock = checkout, origin, fetcher, clock
        self._key = delivery_key.encode()
        self.payment_app = create_wsgi_app(checkout)
        with checkout._db() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS runtime_configuration (id INTEGER PRIMARY KEY CHECK(id=1), key_check TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS runtime_jobs (order_id TEXT PRIMARY KEY REFERENCES jobs(order_id),
                attempts INTEGER NOT NULL DEFAULT 0, lease_id TEXT, retry_at INTEGER NOT NULL DEFAULT 0, error TEXT);
              CREATE TABLE IF NOT EXISTS report_access (order_id TEXT PRIMARY KEY REFERENCES orders(order_id),
                expires INTEGER NOT NULL, received_at INTEGER, artifact_sha256 TEXT);
            """)
            check = hmac.new(self._key, b"commercelint-delivery-key-check", hashlib.sha256).hexdigest()
            db.execute("INSERT OR IGNORE INTO runtime_configuration VALUES(1,?)", (check,))
            if not hmac.compare_digest(db.execute("SELECT key_check FROM runtime_configuration").fetchone()[0], check):
                raise PaymentError("Delivery key changed for this store; restore its protected key before serving.")

    def _token(self, order_id):
        return hmac.new(self._key, (self.checkout.config.mode + ":" + order_id).encode(), hashlib.sha256).hexdigest()

    def access(self, order_id, token):
        if not isinstance(order_id, str) or not ORDER.fullmatch(order_id) or not isinstance(token, str):
            raise PaymentError("Private report access is invalid or expired.")
        if not hmac.compare_digest(self._token(order_id), token):
            raise PaymentError("Private report access is invalid or expired.")
        with self.checkout._db() as db:
            row = db.execute("SELECT expires FROM report_access WHERE order_id=?", (order_id,)).fetchone()
            if row is None or row[0] < int(self.clock()):
                raise PaymentError("Private report access is invalid or expired.")

    def work_once(self):
        """One bounded job; no Stripe/model/mail call. Failed fetches stop after 3 attempts."""
        now, lease = int(self.clock()), secrets.token_hex(16)
        with self.checkout._db() as db:
            db.execute("INSERT OR IGNORE INTO runtime_jobs(order_id) SELECT order_id FROM jobs WHERE status='queued'")
            row = db.execute("""SELECT r.order_id,o.intake FROM runtime_jobs r JOIN jobs j USING(order_id)
              JOIN orders o USING(order_id) WHERE j.status='queued' AND o.payment_state='succeeded'
              AND r.attempts<3 AND r.retry_at<=? ORDER BY o.created LIMIT 1""", (now,)).fetchone()
            if row is None:
                return {"status": "idle"}
            oid, intake = row["order_id"], json.loads(row["intake"])
            db.execute("UPDATE runtime_jobs SET attempts=attempts+1,lease_id=?,retry_at=?,error=NULL WHERE order_id=?",
                       (lease, now + 1800, oid))
        try:
            pages = [{"url": url, "html": self.fetcher(url)} for url in intake["urls"]["accepted_urls"]]
            with self.checkout._db() as db:
                current = db.execute("SELECT lease_id FROM runtime_jobs WHERE order_id=?", (oid,)).fetchone()[0]
                if current != lease:
                    return {"status": "lease_lost", "order_id": oid}
            result = self.checkout.stage_report(oid, pages)
        except (FetchError, PaymentError, ValueError, OSError):
            with self.checkout._db() as db:
                db.execute("UPDATE runtime_jobs SET lease_id=NULL,retry_at=?,error='report_fetch_or_render_failed' WHERE order_id=? AND lease_id=?",
                           (int(self.clock()) + 300, oid, lease))
            return {"status": "retry_or_support_required", "order_id": oid}
        with self.checkout._db() as db:
            db.execute("UPDATE runtime_jobs SET lease_id=NULL,error=NULL WHERE order_id=? AND lease_id=?", (oid, lease))
        return {"status": "report_available", "order_id": oid, "report_sha256": result["report_sha256"], "email_sent": False}

    def application(self, environ, start_response):
        path, method = environ.get("PATH_INFO", ""), environ.get("REQUEST_METHOD", "")
        origin = environ.get("HTTP_ORIGIN", "")
        cors = [("Access-Control-Allow-Origin", origin), ("Vary", "Origin")] if origin in {self.origin, CANONICAL} else []

        def respond(status, payload, content_type="application/json"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"), ("X-Content-Type-Options", "nosniff"),
                ("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")] + cors)
            return [body]

        try:
            if method == "GET" and path == "/health":
                return respond("200 OK", {"status": "ok", "mode": self.checkout.config.mode})
            if method == "GET" and path in {"/", "/runtime.js", "/runtime.css"}:
                asset = {"/": "checkout_runtime.html", "/runtime.js": "checkout_runtime.js", "/runtime.css": "checkout_runtime.css"}[path]
                ctype = {"/": "text/html; charset=utf-8", "/runtime.js": "text/javascript; charset=utf-8", "/runtime.css": "text/css; charset=utf-8"}[path]
                return respond("200 OK", (ROOT / "operator" / asset).read_bytes(), ctype)
            if method == "OPTIONS" and cors and path in {"/checkout", "/inquiry", "/report", "/acknowledge"}:
                start_response("204 No Content", cors + [("Access-Control-Allow-Methods", "POST"),
                    ("Access-Control-Allow-Headers", "Content-Type, Authorization"), ("Cache-Control", "no-store")])
                return [b""]
            if path == "/webhook":
                return self.payment_app(environ, start_response)
            if method != "POST" or path not in {"/checkout", "/inquiry", "/report", "/acknowledge"}:
                return respond("404 Not Found", {"error": "Route not found."})
            if not cors or environ.get("CONTENT_TYPE", "").split(";", 1)[0] != "application/json":
                raise PaymentError("Use an allowed site origin and JSON input.")
            length = int(environ.get("CONTENT_LENGTH", "0"))
            if not 0 < length <= MAX_BODY:
                raise PaymentError("A bounded request body is required.")
            raw = environ["wsgi.input"].read(length)
            if len(raw) != length:
                raise PaymentError("Incomplete request body.")
            if path in {"/checkout", "/inquiry"}:
                delegated = dict(environ, PATH_INFO="/checkout", HTTP_ORIGIN=CANONICAL)
                delegated["wsgi.input"] = io.BytesIO(raw)
                statuses = []
                body = b"".join(self.payment_app(delegated, lambda s, h: statuses.append(s)))
                result = json.loads(body)
                if statuses[0] == "200 OK":
                    oid = result["order_id"]
                    with self.checkout._db() as db:
                        db.execute("INSERT OR IGNORE INTO report_access(order_id,expires) VALUES(?,?)", (oid, int(self.clock()) + 30 * 86400))
                    result.update(report_token=self._token(oid), delivery="private_browser", email_sent=False)
                return respond(statuses[0], result)
            fields = json.loads(raw)
            expected = {"order_id"} if path == "/report" else {"order_id", "artifact_sha256"}
            if not isinstance(fields, dict) or set(fields) != expected:
                raise PaymentError("Invalid private report request.")
            oid = fields["order_id"]
            authorization = environ.get("HTTP_AUTHORIZATION", "")
            token = authorization[7:] if authorization.startswith("Bearer ") else ""
            self.access(oid, token)
            with self.checkout._db() as db:
                row = db.execute("SELECT o.payment_state,j.status,j.report_markdown,r.attempts,r.error,r.retry_at FROM orders o LEFT JOIN jobs j USING(order_id) LEFT JOIN runtime_jobs r USING(order_id) WHERE o.order_id=?", (oid,)).fetchone()
                if row["status"] != "staged":
                    exhausted = row["attempts"] and row["attempts"] >= 3 and (row["error"] or row["retry_at"] <= int(self.clock()))
                    status = "support_required" if exhausted else row["status"] or row["payment_state"]
                    return respond("202 Accepted", {"order_id": oid, "status": status})
                markdown = row["report_markdown"]
                digest = hashlib.sha256(markdown.encode()).hexdigest()
                if path == "/acknowledge":
                    if not isinstance(fields["artifact_sha256"], str) or not hmac.compare_digest(digest, fields["artifact_sha256"]):
                        raise PaymentError("Report acknowledgement does not match the artifact.")
                    db.execute("UPDATE report_access SET received_at=COALESCE(received_at,?),artifact_sha256=? WHERE order_id=?", (int(self.clock()), digest, oid))
                    return respond("200 OK", {"status": "client_receipt_recorded", "email_sent": False})
                return respond("200 OK", {"order_id": oid, "status": "report_available", "markdown": markdown,
                    "artifact_sha256": digest, "email_sent": False})
        except (PaymentError, ValueError, TypeError, UnicodeError):
            return respond("400 Bad Request", {"error": "Request or private access is invalid. Check input or contact support."})
        except (sqlite3.Error, OSError):
            return respond("503 Service Unavailable", {"error": "Private report service unavailable; retry the same request."})


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass  # Do not log customer URLs, body, tokens, or private order identifiers.


def runtime_from_environment():
    return CheckoutRuntime(StripeCheckout(StripeConfig.from_environment()),
        delivery_key=os.environ.get("COMMERCELINT_DELIVERY_KEY", ""),
        origin=os.environ.get("COMMERCELINT_RUNTIME_ORIGIN", ""))


def create_application():
    """WSGI factory for an already-qualified HTTPS host, using protected env."""
    return runtime_from_environment().application


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check-config", "serve-local", "work-once"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        if args.config:
            load_protected_environment(args.config)
        runtime = runtime_from_environment()
        config = runtime.checkout.config
        if args.command == "check-config":
            print(json.dumps({"status": "configuration_valid", "mode": config.mode, "provider_contacted": False}))
        elif args.command == "work-once":
            print(json.dumps(runtime.work_once()))
        else:
            if config.mode != "test" or runtime.origin != f"http://127.0.0.1:{args.port}":
                raise PaymentError("The built-in development server requires test mode and its exact loopback origin.")
            print(json.dumps({"status": "listening", "origin": runtime.origin, "mode": "test"}), flush=True)
            with make_server("127.0.0.1", args.port, runtime.application, handler_class=QuietHandler) as server:
                server.serve_forever()
        return 0
    except (PaymentError, ValueError, OSError, sqlite3.Error):
        print(json.dumps({"status": "configuration_or_runtime_error", "details": "Verify protected mode, keys, paths and origin; no provider success is implied."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
