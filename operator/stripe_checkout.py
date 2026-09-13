"""Real Stripe Checkout adapter; private state, no keys or customer data in Git.

The HTTP host passes raw webhook bytes and Stripe-Signature to handle_webhook.
Checkout redirects never establish payment. Configuration is operator-supplied.
No network calls happen at import, during configuration, or in webhook handling.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    from .private_intake import validate_intake_request
    from .paid_report import page_reports_from_html, render_paid_markdown
except ImportError:
    from private_intake import validate_intake_request
    from paid_report import page_reports_from_html, render_paid_markdown

ROOT = Path(__file__).resolve().parents[1]
AMOUNTS = {"sample": 199, "lite": 999, "comprehensive": 1999}
MAX_BODY = 262144
STRIPE_API = "https://api.stripe.com/v1/checkout/sessions"
EVENT_TYPES = {
    "checkout.session.completed", "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed", "checkout.session.expired",
}


class PaymentError(ValueError):
    """Safe message for the host; never contains credentials/provider bodies."""


class ProviderUnavailable(RuntimeError):
    """Retry with the same request ID; never create a replacement blindly."""


@dataclass(frozen=True)
class StripeConfig:
    mode: str
    api_key: str = field(repr=False)
    webhook_secret: str = field(repr=False)
    database_path: Path
    success_url: str
    cancel_url: str

    def __post_init__(self):
        if self.mode not in {"test", "live"}:
            raise PaymentError("Stripe mode must be explicitly test or live.")
        if not re.fullmatch(rf"(?:sk|rk)_{self.mode}_[A-Za-z0-9]+", self.api_key):
            raise PaymentError("Stripe key does not match the configured mode.")
        if not re.fullmatch(r"whsec_[A-Za-z0-9]+", self.webhook_secret):
            raise PaymentError("A Stripe endpoint signing secret is required.")
        db = Path(self.database_path).expanduser()
        if not db.is_absolute() or db.resolve().is_relative_to(ROOT):
            raise PaymentError("Payment storage must be an absolute private path outside this repository.")
        object.__setattr__(self, "database_path", db.resolve())
        for url in (self.success_url, self.cancel_url):
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or parsed.hostname != "priyanshchordia.com"
                    or parsed.username or parsed.password or parsed.port not in (None, 443)
                    or not parsed.path.startswith("/commercelint/") or parsed.fragment):
                raise PaymentError("Checkout return URLs must use the canonical CommerceLint HTTPS path.")

    @classmethod
    def from_environment(cls):
        mode = os.environ.get("COMMERCELINT_STRIPE_MODE", "")
        if mode not in {"test", "live"}:
            raise PaymentError("Set COMMERCELINT_STRIPE_MODE to test or live.")
        prefix = f"COMMERCELINT_STRIPE_{mode.upper()}_"
        return cls(mode, os.environ.get(prefix + "SECRET_KEY", ""),
                   os.environ.get(prefix + "WEBHOOK_SECRET", ""),
                   Path(os.environ.get(prefix + "DB_PATH", "")),
                   os.environ.get("COMMERCELINT_CHECKOUT_SUCCESS_URL", ""),
                   os.environ.get("COMMERCELINT_CHECKOUT_CANCEL_URL", ""))


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def stripe_post(fields: dict[str, str], headers: dict[str, str]) -> dict:
    """One bounded provider call. Never forward Authorization across redirects."""
    request = Request(STRIPE_API, data=urlencode(fields).encode(), headers=headers, method="POST")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=20) as response:
            raw = response.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY:
                raise ProviderUnavailable("Stripe response exceeded the size limit.")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Unexpected response")
            return data
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderUnavailable("Stripe Checkout was not confirmed; retry the same request ID.") from None


def verify_stripe_event(payload: bytes, signature: str, secret: str, *, now: int | None = None) -> dict:
    """Stripe v1 HMAC over timestamp.raw_body, with a five-minute clock window."""
    if not isinstance(payload, bytes) or len(payload) > MAX_BODY or len(signature) > 4096:
        raise PaymentError("Invalid webhook payload or signature.")
    timestamps, signatures = [], []
    for part in signature.split(","):
        key, sep, value = part.strip().partition("=")
        if sep and key == "t":
            timestamps.append(value)
        elif sep and key == "v1":
            signatures.append(value)
    if len(timestamps) != 1 or not re.fullmatch(r"[0-9]{1,12}", timestamps[0]):
        raise PaymentError("Invalid webhook timestamp.")
    timestamp = int(timestamps[0])
    if abs((int(time.time()) if now is None else now) - timestamp) > 300:
        raise PaymentError("Webhook signature timestamp is outside tolerance.")
    if not secret.startswith("whsec_"):
        raise PaymentError("Stripe endpoint signing secret is missing.")
    expected = hmac.new(secret.encode(), timestamps[0].encode() + b"." + payload, hashlib.sha256).hexdigest()
    if not any(re.fullmatch(r"[a-fA-F0-9]{64}", candidate)
               and hmac.compare_digest(expected, candidate.lower()) for candidate in signatures):
        raise PaymentError("Webhook signature verification failed.")
    try:
        event = json.loads(payload)
    except (ValueError, UnicodeError):
        raise PaymentError("Webhook is not valid JSON.") from None
    if not isinstance(event, dict) or not re.fullmatch(r"evt_[A-Za-z0-9]+", str(event.get("id", ""))):
        raise PaymentError("Webhook event ID is invalid.")
    return event


class StripeCheckout:
    def __init__(self, config: StripeConfig, *, transport: Callable = stripe_post, clock: Callable = time.time):
        self.config, self.transport, self.clock = config, transport, clock
        directory = config.database_path.parent
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix" and directory.stat().st_mode & 0o077:
            raise PaymentError("Use an owner-only directory for private payment storage.")
        # Exclusive creation protects the database before SQLite opens it.
        fd = os.open(config.database_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        if os.name == "posix" and config.database_path.stat().st_mode & 0o077:
            raise PaymentError("Private payment database must be owner-only.")
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS configuration (id INTEGER PRIMARY KEY CHECK(id=1), mode TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS orders (
                  order_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, plan_id TEXT NOT NULL,
                  amount INTEGER NOT NULL, intake TEXT NOT NULL, delivery_email TEXT NOT NULL,
                  checkout_fields TEXT,
                  created INTEGER NOT NULL, session_id TEXT UNIQUE, checkout_url TEXT,
                  payment_state TEXT NOT NULL DEFAULT 'pending_checkout');
                CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, order_id TEXT NOT NULL,
                  event_type TEXT NOT NULL, received INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (order_id TEXT PRIMARY KEY REFERENCES orders(order_id),
                  status TEXT NOT NULL DEFAULT 'queued', report_json TEXT, report_markdown TEXT,
                  report_sha256 TEXT, delivery_status TEXT NOT NULL DEFAULT 'not_delivered');
            """)
            if "checkout_fields" not in {row[1] for row in db.execute("PRAGMA table_info(orders)")}:
                db.execute("ALTER TABLE orders ADD COLUMN checkout_fields TEXT")
            db.execute("INSERT OR IGNORE INTO configuration VALUES (1, ?)", (config.mode,))
            if db.execute("SELECT mode FROM configuration WHERE id=1").fetchone()[0] != config.mode:
                raise PaymentError("Refusing to mix Stripe test and live databases.")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.config.database_path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def create_checkout(self, *, request_id: str, plan_id: str, urls: list[str], contact_email: str,
                        claimed_price=None) -> dict:
        if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", request_id):
            raise PaymentError("Use a stable random request ID of 16–128 URL-safe characters.")
        if not isinstance(plan_id, str) or plan_id not in AMOUNTS:
            raise PaymentError("Unknown one-time payment plan.")
        if not isinstance(contact_email, str) or len(contact_email) > 254:
            raise PaymentError("Invalid delivery email.")
        if not isinstance(urls, list) or not 1 <= len(urls) <= 15 or any(not isinstance(u, str) or len(u) > 2048 for u in urls):
            raise PaymentError("Invalid product URL list.")
        try:
            intake = validate_intake_request(plan_id=plan_id, urls=urls, contact_email=contact_email,
                                             claimed_price=claimed_price, resolve_dns=True)
        except (ValueError, TypeError, ArithmeticError):
            raise PaymentError("Invalid intake or finite one-time price.") from None
        if not intake.get("charge_allowed"):
            raise PaymentError(intake.get("error") or "Intake rejected before payment.")
        amount = AMOUNTS.get(plan_id)
        if amount is None or intake["price_usd"] != amount / 100:
            raise PaymentError("Plan price does not match the authorized one-time tier.")
        oid = "ord_" + hashlib.sha256(f"{self.config.mode}:{request_id}".encode()).hexdigest()[:32]
        fingerprint = intake["inquiry_id"]
        fields = {
            "mode": "payment", "payment_method_types[0]": "card", "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][unit_amount]": str(amount),
            "line_items[0][price_data][product_data][name]": "CommerceLint " + intake["plan"]["name"],
            "client_reference_id": oid, "metadata[order_id]": oid, "metadata[plan_id]": plan_id,
            "metadata[project_id]": "commercelint", "customer_email": contact_email.strip(),
            "success_url": self.config.success_url, "cancel_url": self.config.cancel_url,
        }
        with self._db() as db:
            existing = db.execute("SELECT * FROM orders WHERE order_id=?", (oid,)).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise PaymentError("Request ID was already bound to different intake.")
                if existing["payment_state"] == "succeeded":
                    return {"order_id": oid, "mode": self.config.mode, "payment_state": "succeeded", "checkout_url": None}
                if int(self.clock()) - existing["created"] >= 23 * 3600 or existing["payment_state"] in {"expired", "failed"}:
                    raise PaymentError("Checkout needs reconciliation before a new payment attempt.")
                if existing["session_id"]:
                    return {"order_id": oid, "mode": self.config.mode, "payment_state": existing["payment_state"],
                            "session_id": existing["session_id"], "checkout_url": existing["checkout_url"]}
                if not existing["checkout_fields"]:
                    raise PaymentError("Earlier checkout lacks its original provider request; reconcile before retrying.")
                # Stripe requires identical parameters, including redirects and email
                # spelling, for the same idempotency key after a lost response.
                fields = json.loads(existing["checkout_fields"])
            else:
                db.execute("INSERT INTO orders (order_id,fingerprint,plan_id,amount,intake,delivery_email,created,checkout_fields) VALUES (?,?,?,?,?,?,?,?)",
                           (oid, fingerprint, plan_id, amount, json.dumps(intake), contact_email.strip(), int(self.clock()), json.dumps(fields)))
        session = self.transport(fields, {"Authorization": "Bearer " + self.config.api_key,
                                          "Content-Type": "application/x-www-form-urlencoded",
                                          "Idempotency-Key": f"commercelint:{self.config.mode}:{oid}"})
        self._validate_session(session, oid, plan_id, amount)
        url = urlsplit(str(session.get("url", "")))
        if url.scheme != "https" or url.netloc != "checkout.stripe.com":
            raise ProviderUnavailable("Stripe did not return a supported hosted Checkout URL.")
        with self._db() as db:
            prior = db.execute("SELECT session_id FROM orders WHERE order_id=?", (oid,)).fetchone()[0]
            if prior and prior != session["id"]:
                raise PaymentError("Provider returned conflicting sessions for one request.")
            db.execute("UPDATE orders SET session_id=?,checkout_url=? WHERE order_id=?",
                       (session["id"], session["url"], oid))
        return {"order_id": oid, "mode": self.config.mode, "session_id": session["id"],
                "checkout_url": session["url"], "payment_state": "pending_checkout"}

    def _validate_session(self, session: dict, oid: str, plan: str, amount: int):
        if not isinstance(session, dict):
            raise PaymentError("Stripe session response is malformed.")
        metadata = session.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise PaymentError("Stripe session metadata is malformed.")
        if (session.get("object") != "checkout.session" or session.get("mode") != "payment"
                or session.get("livemode") is not (self.config.mode == "live")
                or not re.fullmatch(rf"cs_{self.config.mode}_[A-Za-z0-9]+", str(session.get("id", "")))
                or session.get("client_reference_id") != oid
                or metadata.get("project_id") != "commercelint" or metadata.get("order_id") != oid
                or metadata.get("plan_id") != plan or type(session.get("amount_total")) is not int
                or session["amount_total"] != amount or session.get("currency") != "usd"):
            raise PaymentError("Stripe session does not match the private order, amount, currency or mode.")

    def handle_webhook(self, payload: bytes, signature_header: str) -> dict:
        event = verify_stripe_event(payload, signature_header, self.config.webhook_secret, now=int(self.clock()))
        if event.get("livemode") is not (self.config.mode == "live") or event.get("account"):
            raise PaymentError("Webhook account/mode does not match this direct Stripe integration.")
        if not isinstance(event.get("type"), str):
            raise PaymentError("Webhook event type is invalid.")
        if event["type"] not in EVENT_TYPES:
            return {"accepted": True, "ignored": True}
        data = event.get("data")
        session = data.get("object") if isinstance(data, dict) else None
        if not isinstance(session, dict):
            raise PaymentError("Webhook has no Checkout Session snapshot.")
        metadata = session.get("metadata")
        if isinstance(metadata, dict) and metadata.get("project_id") and metadata["project_id"] != "commercelint":
            return {"accepted": True, "ignored": True}  # Another product on the same direct account.
        oid = session.get("client_reference_id")
        if not isinstance(oid, str) or not re.fullmatch(r"ord_[a-f0-9]{32}", oid):
            raise PaymentError("Webhook order reference is invalid.")
        with self._db() as db:
            order = db.execute("SELECT * FROM orders WHERE order_id=?", (oid,)).fetchone()
            if order is None:
                raise PaymentError("Webhook refers to an unknown private order.")
            self._validate_session(session, oid, order["plan_id"], order["amount"])
            if not order["session_id"]:
                # A provider callback can beat the Checkout API response. Retry after binding.
                raise ProviderUnavailable("Checkout session binding is not yet durable; retry webhook.")
            if order["session_id"] != session["id"]:
                raise PaymentError("Webhook session is not the order's bound Checkout Session.")
            prior = db.execute("SELECT order_id FROM events WHERE event_id=?", (event["id"],)).fetchone()
            if prior:
                if prior["order_id"] != oid:
                    raise PaymentError("Webhook event ID is already bound to another order.")
                return {"accepted": True, "duplicate": True, "order_id": oid, "mode": self.config.mode}
            kind = event["type"]
            paid = kind in {"checkout.session.completed", "checkout.session.async_payment_succeeded"} and session.get("payment_status") == "paid"
            if paid and session.get("status") != "complete":
                raise PaymentError("Paid Checkout Session is not complete.")
            if kind == "checkout.session.async_payment_succeeded" and not paid:
                raise PaymentError("Payment-success event is not actually paid.")
            next_state = ("succeeded" if paid else "expired" if kind.endswith(".expired")
                          else "failed" if kind.endswith("_failed") else "awaiting_payment")
            if order["payment_state"] == "succeeded":
                next_state = "succeeded"  # Late failure/expiry cannot undo a paid receipt.
            db.execute("INSERT INTO events VALUES (?,?,?,?)", (event["id"], oid, kind, int(self.clock())))
            db.execute("UPDATE orders SET payment_state=? WHERE order_id=?", (next_state, oid))
            if paid:
                db.execute("INSERT OR IGNORE INTO jobs (order_id) VALUES (?)", (oid,))
        return {"accepted": True, "duplicate": False, "order_id": oid, "mode": self.config.mode,
                "payment_state": next_state, "fulfillment_queued": paid, "revenue_verified": False}

    def stage_report(self, order_id: str, pages: list[dict[str, str]]) -> dict:
        """Trusted fulfillment worker supplies fetched pages; no fetching or email here."""
        with self._db() as db:
            job = db.execute("SELECT * FROM jobs WHERE order_id=?", (order_id,)).fetchone()
            order = db.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
            if job is None or order is None or order["payment_state"] != "succeeded":
                raise PaymentError("Report fulfillment requires a verified payment and queued job.")
            if job["status"] == "staged":
                return {"order_id": order_id, "status": "staged", "duplicate": True,
                        "report_sha256": job["report_sha256"], "delivery_status": job["delivery_status"]}
            intake = json.loads(order["intake"])
            if sorted(p.get("url", "") for p in pages) != sorted(intake["urls"]["accepted_urls"]):
                raise PaymentError("Report pages differ from the paid URL scope.")
            report = page_reports_from_html(order["plan_id"], pages, order_id=order_id, resolve_dns=False)
            db.execute("UPDATE jobs SET status='staged',report_json=?,report_markdown=?,report_sha256=? WHERE order_id=?",
                       (json.dumps(report), render_paid_markdown(report), report["report_sha256"], order_id))
            return {"order_id": order_id, "status": "staged", "duplicate": False,
                    "report_sha256": report["report_sha256"], "delivery_status": "not_delivered"}


def create_wsgi_app(checkout: StripeCheckout):
    """Mount behind an HTTPS host; static GitHub Pages cannot run this service.

    The host owns rate limiting, TLS and protected runtime configuration. This
    factory does not start a server, create a Stripe endpoint or change the site.
    """
    def application(environ, start_response):
        origin = environ.get("HTTP_ORIGIN", "")
        cors = [("Access-Control-Allow-Origin", origin), ("Vary", "Origin")] if origin == "https://priyanshchordia.com" else []
        try:
            path, method = environ.get("PATH_INFO", ""), environ.get("REQUEST_METHOD", "")
            if path == "/checkout" and method == "OPTIONS" and cors:
                start_response("204 No Content", cors + [("Access-Control-Allow-Methods", "POST"),
                    ("Access-Control-Allow-Headers", "Content-Type")])
                return [b""]
            if path not in {"/checkout", "/webhook"} or method != "POST":
                status, result = "404 Not Found", {"error": "Route not found."}
            else:
                try:
                    length = int(environ.get("CONTENT_LENGTH", ""))
                except (ValueError, TypeError):
                    raise PaymentError("A bounded Content-Length is required.") from None
                if not 0 < length <= MAX_BODY:
                    raise PaymentError("Request body exceeds the permitted size.")
                raw = environ["wsgi.input"].read(length)
                if len(raw) != length:
                    raise PaymentError("Incomplete request body.")
                if path == "/webhook":
                    result = checkout.handle_webhook(raw, environ.get("HTTP_STRIPE_SIGNATURE", ""))
                else:
                    if not cors or environ.get("CONTENT_TYPE", "").split(";", 1)[0] != "application/json":
                        raise PaymentError("Checkout requires the canonical site origin and JSON input.")
                    try:
                        fields = json.loads(raw)
                    except (ValueError, UnicodeError):
                        raise PaymentError("Invalid checkout JSON.") from None
                    required = {"request_id", "plan_id", "urls", "contact_email"}
                    if not isinstance(fields, dict) or not required <= fields.keys() or fields.keys() - required - {"claimed_price"}:
                        raise PaymentError("Invalid checkout fields.")
                    result = checkout.create_checkout(**fields)
                status = "200 OK"
        except PaymentError as exc:
            status, result = "400 Bad Request", {"error": str(exc)}
        except (ProviderUnavailable, sqlite3.Error):
            status, result = "503 Service Unavailable", {"error": "Payment service unavailable; retry the same request."}
        body = json.dumps(result).encode()
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body))),
                                ("Cache-Control", "no-store")] + cors)
        return [body]
    return application
