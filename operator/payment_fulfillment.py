#!/usr/bin/env python3
"""CommerceLint checkout → verified payment → durable report fulfillment (H04).

Stripe account activation may be blocked. This module binds validated plans to
orders, verifies webhook events with replay protection, runs one durable report
job, and stages private delivery / refund-support records. No real revenue is
claimed from test fixtures.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

try:
    from .customer_ops import build_event, process_customer_event
    from .paid_report import page_reports_from_html, render_paid_markdown
    from .plans import assert_plan_price, get_plan, load_plans_config
    from .private_intake import validate_intake_request
except ImportError:
    from customer_ops import build_event, process_customer_event
    from paid_report import page_reports_from_html, render_paid_markdown
    from plans import assert_plan_price, get_plan, load_plans_config
    from private_intake import validate_intake_request

ROOT = Path(__file__).resolve().parents[1]
ORDERS_PATH = ROOT / "state" / "orders.json"
JOBS_PATH = ROOT / "state" / "fulfillment_jobs.json"
WEBHOOK_PATH = ROOT / "state" / "payment_webhooks.json"
SUPPORT_PATH = ROOT / "state" / "support_cases.json"
REPORTS_DIR = ROOT / "state" / "reports"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def order_id_for(inquiry_id: str, plan_id: str) -> str:
    digest = hashlib.sha256(f"{inquiry_id}|{plan_id}".encode("utf-8")).hexdigest()[:20]
    return f"ord_{digest}"


def create_pending_order(
    *,
    plan_id: str,
    urls: list[str],
    contact_email: str,
    claimed_price: Any | None = None,
    resolve_dns: bool = False,
    orders_path: Path | None = None,
) -> dict[str, Any]:
    intake = validate_intake_request(
        plan_id=plan_id,
        urls=urls,
        contact_email=contact_email,
        claimed_price=claimed_price,
        resolve_dns=resolve_dns,
    )
    if not intake.get("charge_allowed"):
        return {
            "ok": False,
            "charge_allowed": False,
            "error": intake.get("error"),
            "intake": intake,
            "order": None,
        }

    plan = intake["plan"]
    oid = order_id_for(intake["inquiry_id"], plan["id"])
    order = {
        "order_id": oid,
        "inquiry_id": intake["inquiry_id"],
        "project_id": "commercelint",
        "plan_id": plan["id"],
        "price_usd": float(assert_plan_price(plan["id"], plan["price_usd"])),
        "currency": "USD",
        "accepted_urls": intake["urls"]["accepted_urls"],
        "contact_email_fingerprint": intake["contact_email_fingerprint"],
        "payment_state": "pending_checkout",
        "provider": "stripe_checkout_placeholder",
        "provider_session_id": None,
        "checkout_status": "not_connected",
        "created_at_utc": now_iso(),
        "updated_at_utc": now_iso(),
    }
    path = orders_path or ORDERS_PATH
    store = load_json(path, {"schema_version": 1, "orders": []})
    existing = next((item for item in store["orders"] if item["order_id"] == oid), None)
    if existing is None:
        store["orders"].append(order)
    else:
        # Immutable plan/amount/urls once created; only refresh updated_at when still pending.
        if existing.get("payment_state") == "pending_checkout":
            existing["updated_at_utc"] = now_iso()
            order = existing
        else:
            order = existing
    store["updated_at_utc"] = now_iso()
    write_json(path, store)
    return {"ok": True, "charge_allowed": True, "order": order, "intake": intake}


def verify_webhook_signature(payload: bytes, secret: str, signature_header: str) -> bool:
    """Minimal HMAC check for staged providers. Empty secret refuses verification."""
    if not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    provided = signature_header.strip()
    if provided.startswith("sha256="):
        provided = provided.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


def record_payment_webhook(
    *,
    provider_event_id: str,
    order_id: str,
    payment_state: str,
    amount_usd: Any,
    signature_ok: bool,
    raw_type: str,
    webhooks_path: Path | None = None,
    orders_path: Path | None = None,
) -> dict[str, Any]:
    if not signature_ok:
        return {
            "ok": False,
            "accepted": False,
            "error": "Webhook signature verification failed; payment state unchanged.",
            "duplicate": False,
        }

    path = webhooks_path or WEBHOOK_PATH
    store = load_json(path, {"schema_version": 1, "events": []})
    existing = next((item for item in store["events"] if item.get("provider_event_id") == provider_event_id), None)
    if existing is not None:
        return {
            "ok": True,
            "accepted": True,
            "duplicate": True,
            "event": existing,
            "note": "Replay ignored; no duplicate fulfillment.",
        }

    amount = Decimal(str(amount_usd)).quantize(Decimal("0.01"))
    # Validate amount against order plan when order exists.
    orders = load_json(orders_path or ORDERS_PATH, {"orders": []})
    order = next((item for item in orders.get("orders", []) if item.get("order_id") == order_id), None)
    if order is None:
        return {"ok": False, "accepted": False, "error": f"Unknown order_id {order_id}", "duplicate": False}
    expected = Decimal(str(order["price_usd"])).quantize(Decimal("0.01"))
    if amount != expected:
        return {
            "ok": False,
            "accepted": False,
            "error": f"Webhook amount {amount} does not match order price {expected}.",
            "duplicate": False,
        }

    event = {
        "provider_event_id": provider_event_id,
        "order_id": order_id,
        "payment_state": payment_state,
        "amount_usd": float(expected),
        "raw_type": raw_type,
        "received_at_utc": now_iso(),
        "idempotency_key": hashlib.sha256(provider_event_id.encode("utf-8")).hexdigest(),
    }
    store["events"].append(event)
    store["updated_at_utc"] = now_iso()
    write_json(path, store)

    if payment_state == "succeeded":
        order["payment_state"] = "succeeded"
        order["updated_at_utc"] = now_iso()
    elif payment_state == "failed":
        order["payment_state"] = "failed"
        order["updated_at_utc"] = now_iso()
    elif payment_state == "refunded":
        order["payment_state"] = "refunded"
        order["updated_at_utc"] = now_iso()
    write_json(orders_path or ORDERS_PATH, orders)

    return {"ok": True, "accepted": True, "duplicate": False, "event": event, "order": order}


def enqueue_fulfillment_job(
    order: dict[str, Any],
    *,
    jobs_path: Path | None = None,
) -> dict[str, Any]:
    if order.get("payment_state") != "succeeded":
        raise ValueError("Fulfillment requires authoritative payment_state=succeeded.")
    job_id = f"job_{order['order_id'][4:]}"
    path = jobs_path or JOBS_PATH
    store = load_json(path, {"schema_version": 1, "jobs": []})
    existing = next((item for item in store["jobs"] if item.get("job_id") == job_id), None)
    if existing is not None:
        return existing
    job = {
        "job_id": job_id,
        "order_id": order["order_id"],
        "plan_id": order["plan_id"],
        "accepted_urls": order["accepted_urls"],
        "status": "queued",
        "attempts": 0,
        "created_at_utc": now_iso(),
        "updated_at_utc": now_iso(),
        "report_sha256": None,
        "delivery_status": "not_delivered",
    }
    store["jobs"].append(job)
    store["updated_at_utc"] = now_iso()
    write_json(path, store)
    return job


def run_fulfillment_job(
    job: dict[str, Any],
    pages: list[dict[str, str]],
    *,
    jobs_path: Path | None = None,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    report = page_reports_from_html(
        job["plan_id"],
        pages,
        order_id=job["order_id"],
        resolve_dns=False,
    )
    out_dir = reports_dir or REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{job['order_id']}.json"
    md_path = out_dir / f"{job['order_id']}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_paid_markdown(report), encoding="utf-8")

    path = jobs_path or JOBS_PATH
    store = load_json(path, {"schema_version": 1, "jobs": []})
    current = next(item for item in store["jobs"] if item["job_id"] == job["job_id"])
    current["status"] = "fulfilled"
    current["attempts"] = int(current.get("attempts") or 0) + 1
    current["report_sha256"] = report["report_sha256"]
    current["report_json_path"] = str(json_path)
    current["report_markdown_path"] = str(md_path)
    current["delivery_status"] = "staged_private_delivery"
    current["updated_at_utc"] = now_iso()
    store["updated_at_utc"] = now_iso()
    write_json(path, store)
    return current


def open_support_case(
    *,
    order_id: str,
    reason: str,
    requested_remedy: str,
    support_path: Path | None = None,
) -> dict[str, Any]:
    case_id = f"sup_{hashlib.sha256(f'{order_id}|{reason}'.encode('utf-8')).hexdigest()[:16]}"
    path = support_path or SUPPORT_PATH
    store = load_json(path, {"schema_version": 1, "cases": []})
    existing = next((item for item in store["cases"] if item.get("case_id") == case_id), None)
    if existing is not None:
        return existing
    case = {
        "case_id": case_id,
        "order_id": order_id,
        "project_id": "commercelint",
        "reason": reason,
        "requested_remedy": requested_remedy,
        "status": "open",
        "refund_provider_receipt": None,
        "created_at_utc": now_iso(),
        "updated_at_utc": now_iso(),
        "owner_route": "pchordia@unsubscriber.me",
    }
    store["cases"].append(case)
    write_json(path, store)
    return case


def checkout_to_fulfilled_demo(
    *,
    plan_id: str,
    urls: list[str],
    contact_email: str,
    pages: list[dict[str, str]],
    provider_event_id: str,
    webhook_secret: str = "test_secret",
    root: Path | None = None,
) -> dict[str, Any]:
    """End-to-end local demo: validate → pending order → signed webhook → one job → report."""
    base = root or Path(tempfile_dir())
    orders_path = base / "orders.json"
    webhooks_path = base / "webhooks.json"
    jobs_path = base / "jobs.json"
    reports_dir = base / "reports"
    support_path = base / "support.json"

    created = create_pending_order(
        plan_id=plan_id,
        urls=urls,
        contact_email=contact_email,
        resolve_dns=False,
        orders_path=orders_path,
    )
    if not created["ok"]:
        return created
    order = created["order"]
    payload = json.dumps(
        {"id": provider_event_id, "order_id": order["order_id"], "amount": order["price_usd"]}
    ).encode("utf-8")
    signature = "sha256=" + hmac.new(webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    if not verify_webhook_signature(payload, webhook_secret, signature):
        return {"ok": False, "error": "local signature failed"}

    paid = record_payment_webhook(
        provider_event_id=provider_event_id,
        order_id=order["order_id"],
        payment_state="succeeded",
        amount_usd=order["price_usd"],
        signature_ok=True,
        raw_type="checkout.session.completed",
        webhooks_path=webhooks_path,
        orders_path=orders_path,
    )
    # Replay
    replay = record_payment_webhook(
        provider_event_id=provider_event_id,
        order_id=order["order_id"],
        payment_state="succeeded",
        amount_usd=order["price_usd"],
        signature_ok=True,
        raw_type="checkout.session.completed",
        webhooks_path=webhooks_path,
        orders_path=orders_path,
    )
    job = enqueue_fulfillment_job(paid["order"], jobs_path=jobs_path)
    fulfilled = run_fulfillment_job(job, pages, jobs_path=jobs_path, reports_dir=reports_dir)
    event = build_event(
        project_id="commercelint",
        event_type="payment.succeeded",
        source_ref="payment_fulfillment",
        order_reference=order["order_id"],
        inquiry_reference=order["inquiry_id"],
        provider_reference=provider_event_id,
        payment_state="succeeded",
    )
    ops = process_customer_event(event, contact_fingerprint=order["contact_email_fingerprint"], outbox_path=base / "outbox.json")
    return {
        "ok": True,
        "order": paid["order"],
        "webhook_duplicate_replay": replay["duplicate"],
        "job": fulfilled,
        "customer_ops": ops,
        "support_contact": "pchordia@unsubscriber.me",
        "checkout_live": False,
        "note": "Test/demo path only; Stripe account not connected.",
    }


def tempfile_dir() -> str:
    import tempfile

    return tempfile.mkdtemp(prefix="cl-fulfill-")
