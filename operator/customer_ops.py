#!/usr/bin/env python3
"""Shared customer-operations adapters for CommerceLint (H03).

Commercial destination only. Primandir HubSpot portal writes are refused for
project_id=commercelint. Live HubSpot commercial portal credentials may be
absent; adapters still persist an idempotent outbox for recovery.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENVELOPE_PATH = ROOT / "config" / "event_envelope.json"
OUTBOX_PATH = ROOT / "state" / "customer_ops_outbox.json"
RECOVERY_PATH = ROOT / "state" / "customer_ops_recovery.json"

PRIMANDIR_PORTAL = "primandir_hubspot_246481057"
COMMERCIAL_DESTINATION = "commercelint_private_sheet_or_commercial_portal"
SUPPORT_PATH = ROOT / "state" / "customer_ops_support.json"
OPERATOR_RESPONSES_PATH = ROOT / "state" / "customer_ops_operator_responses.json"

# Consent classes that may upsert a commercial CRM projection (no marketing blast).
CRM_UPSERT_CONSENT = {
    "support_inquiry_only",
    "transactional_order_support",
    "explicit_commercial_opt_in",
}
BLOCKED_CRM_CONSENT = {
    "unknown",
    "marketing_without_opt_in",
    None,
}


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


def load_envelope_config(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or ENVELOPE_PATH).read_text(encoding="utf-8"))


def stable_idempotency_key(*parts: str) -> str:
    material = "|".join(parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_event(
    *,
    project_id: str,
    event_type: str,
    source_ref: str,
    observed_at_utc: str | None = None,
    action_id: str | None = None,
    experiment_id: str | None = None,
    outcome: Any = None,
    measurement_provenance: str | None = None,
    audience_consent_classification: str | None = None,
    provider_reference: str | None = None,
    order_reference: str | None = None,
    inquiry_reference: str | None = None,
    payment_state: str | None = None,
    idempotency_key: str | None = None,
    schema_version: int = 1,
) -> dict[str, Any]:
    key = idempotency_key or stable_idempotency_key(
        project_id,
        event_type,
        source_ref,
        provider_reference or "",
        order_reference or "",
        inquiry_reference or "",
    )
    event_id = f"evt_{key[:24]}"
    return {
        "event_id": event_id,
        "schema_version": schema_version,
        "project_id": project_id,
        "event_type": event_type,
        "source_ref": source_ref,
        "observed_at_utc": observed_at_utc or now_iso(),
        "action_id": action_id,
        "experiment_id": experiment_id,
        "outcome": outcome,
        "measurement_provenance": measurement_provenance,
        "audience_consent_classification": audience_consent_classification,
        "provider_reference": provider_reference,
        "order_reference": order_reference,
        "inquiry_reference": inquiry_reference,
        "payment_state": payment_state,
        "idempotency_key": key,
    }


def resolve_crm_destination(project_id: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config or load_envelope_config()
    project = (payload.get("project_ids") or {}).get(project_id)
    if not project:
        raise ValueError(f"Unknown project_id for CRM routing: {project_id!r}")
    destination = project["crm_destination"]
    forbidden = set(project.get("forbidden_crm_destinations") or [])
    if project_id == "commercelint" and destination == PRIMANDIR_PORTAL:
        raise PermissionError("CommerceLint must not use the Primandir HubSpot portal.")
    if PRIMANDIR_PORTAL in forbidden and destination == PRIMANDIR_PORTAL:
        raise PermissionError(f"Destination {destination} is forbidden for {project_id}.")
    return {
        "project_id": project_id,
        "crm_destination": destination,
        "slack_channel_key": project.get("slack_channel_key"),
        "forbidden_crm_destinations": sorted(forbidden),
        "live_commercial_hubspot_ready": False,
        "note": "Commercial HubSpot portal not established; private sheet remains CommerceLint system of record.",
    }


def refuse_primandir_for_commercelint(project_id: str, requested_destination: str) -> None:
    if project_id == "commercelint" and requested_destination == PRIMANDIR_PORTAL:
        raise PermissionError(
            "Refusing to write CommerceLint leads into Primandir HubSpot portal 246481057."
        )


def consent_allows_crm_upsert(audience_consent_classification: str | None) -> bool:
    return audience_consent_classification in CRM_UPSERT_CONSENT


def upsert_crm_projection(
    event: dict[str, Any],
    *,
    contact_fingerprint: str | None = None,
    requested_destination: str | None = None,
) -> dict[str, Any]:
    project_id = event["project_id"]
    route = resolve_crm_destination(project_id)
    destination = requested_destination or route["crm_destination"]
    refuse_primandir_for_commercelint(project_id, destination)
    if destination != route["crm_destination"] and project_id == "commercelint":
        # Allow explicit commercial destination string only.
        if destination not in {COMMERCIAL_DESTINATION, "commercelint_private_sheet"}:
            raise PermissionError(f"Unsupported CommerceLint CRM destination: {destination}")

    consent = event.get("audience_consent_classification")
    if not consent_allows_crm_upsert(consent):
        return {
            "idempotency_key": event["idempotency_key"],
            "event_id": event["event_id"],
            "project_id": project_id,
            "crm_destination": destination,
            "event_type": event["event_type"],
            "inquiry_reference": event.get("inquiry_reference"),
            "order_reference": event.get("order_reference"),
            "provider_reference": event.get("provider_reference"),
            "payment_state": event.get("payment_state"),
            "contact_fingerprint": contact_fingerprint,
            "audience_consent_classification": consent,
            "status": "skipped_consent",
            "updated_at_utc": now_iso(),
            "note": "CRM upsert skipped; consent class is not allowed for commercial projection.",
        }

    record = {
        "idempotency_key": event["idempotency_key"],
        "event_id": event["event_id"],
        "project_id": project_id,
        "crm_destination": destination,
        "event_type": event["event_type"],
        "inquiry_reference": event.get("inquiry_reference"),
        "order_reference": event.get("order_reference"),
        "provider_reference": event.get("provider_reference"),
        "payment_state": event.get("payment_state"),
        "contact_fingerprint": contact_fingerprint,
        "audience_consent_classification": consent,
        "status": "projected_local",
        "updated_at_utc": now_iso(),
    }
    return record


def build_slack_notification(event: dict[str, Any], crm_record: dict[str, Any]) -> dict[str, Any]:
    route = resolve_crm_destination(event["project_id"])
    return {
        "channel_key": route["slack_channel_key"],
        "idempotency_key": event["idempotency_key"],
        "text": (
            f"[{event['project_id']}] {event['event_type']} "
            f"inquiry={event.get('inquiry_reference') or 'n/a'} "
            f"order={event.get('order_reference') or 'n/a'} "
            f"payment={event.get('payment_state') or 'n/a'}"
        ),
        "response_routing": {
            "mode": "explicit_send_reply_action_required",
            "note": "Internal Slack replies must not auto-send to customers.",
        },
        "crm_link_hint": {
            "destination": crm_record["crm_destination"],
            "event_id": event["event_id"],
        },
        "delivery_status": "staged_not_sent",
    }


def append_outbox(
    event: dict[str, Any],
    crm_record: dict[str, Any],
    slack_payload: dict[str, Any],
    *,
    outbox_path: Path | None = None,
) -> dict[str, Any]:
    path = outbox_path or OUTBOX_PATH
    store = load_json(path, {"schema_version": 1, "updated_at_utc": None, "items": []})
    items = store.setdefault("items", [])
    existing = next((item for item in items if item.get("idempotency_key") == event["idempotency_key"]), None)
    entry = {
        "idempotency_key": event["idempotency_key"],
        "event": event,
        "crm_record": crm_record,
        "slack": slack_payload,
        "status": "pending_delivery",
        "attempts": 0,
        "updated_at_utc": now_iso(),
    }
    if existing is None:
        entry["created_at_utc"] = entry["updated_at_utc"]
        items.append(entry)
        created = True
    else:
        # Replay-safe: keep original created time and do not duplicate.
        entry["created_at_utc"] = existing.get("created_at_utc", entry["updated_at_utc"])
        entry["attempts"] = int(existing.get("attempts") or 0)
        entry["status"] = existing.get("status") or "pending_delivery"
        existing.update(entry)
        entry = existing
        created = False
    store["updated_at_utc"] = now_iso()
    write_json(path, store)
    return {"created": created, "entry": entry}


def enqueue_recovery(
    idempotency_key: str,
    reason: str,
    *,
    recovery_path: Path | None = None,
) -> dict[str, Any]:
    path = recovery_path or RECOVERY_PATH
    store = load_json(path, {"schema_version": 1, "items": []})
    items = store.setdefault("items", [])
    existing = next((item for item in items if item.get("idempotency_key") == idempotency_key), None)
    record = {
        "idempotency_key": idempotency_key,
        "reason": reason,
        "status": "needs_retry",
        "updated_at_utc": now_iso(),
    }
    if existing is None:
        record["created_at_utc"] = record["updated_at_utc"]
        items.append(record)
    else:
        record["created_at_utc"] = existing.get("created_at_utc", record["updated_at_utc"])
        existing.update(record)
        record = existing
    write_json(path, store)
    return record


def process_customer_event(
    event: dict[str, Any],
    *,
    contact_fingerprint: str | None = None,
    outbox_path: Path | None = None,
) -> dict[str, Any]:
    crm_record = upsert_crm_projection(event, contact_fingerprint=contact_fingerprint)
    slack_payload = build_slack_notification(event, crm_record)
    if crm_record.get("status") == "skipped_consent":
        slack_payload["delivery_status"] = "suppressed_consent"
        slack_payload["text"] = (
            f"[{event['project_id']}] consent_skipped {event['event_type']} "
            f"(no CRM upsert; no customer message staged)"
        )
    outbox = append_outbox(event, crm_record, slack_payload, outbox_path=outbox_path)
    return {
        "event_id": event["event_id"],
        "idempotency_key": event["idempotency_key"],
        "crm_record": crm_record,
        "slack": slack_payload,
        "outbox_created": outbox["created"],
        "live_slack_sent": False,
        "live_crm_remote_write": False,
    }


def associate_order_support(
    *,
    inquiry_reference: str | None,
    order_reference: str | None,
    support_reference: str,
    project_id: str = "commercelint",
    note: str | None = None,
    support_path: Path | None = None,
) -> dict[str, Any]:
    """Link inquiry/order identifiers to an explicit support case (local durable record)."""
    path = support_path or SUPPORT_PATH
    destination = resolve_crm_destination(project_id)["crm_destination"]
    refuse_primandir_for_commercelint(project_id, destination)
    store = load_json(path, {"schema_version": 1, "items": []})
    key = stable_idempotency_key(project_id, support_reference, order_reference or "", inquiry_reference or "")
    items = store.setdefault("items", [])
    existing = next((item for item in items if item.get("idempotency_key") == key), None)
    record = {
        "idempotency_key": key,
        "project_id": project_id,
        "support_reference": support_reference,
        "inquiry_reference": inquiry_reference,
        "order_reference": order_reference,
        "note": note,
        "status": "associated_local",
        "updated_at_utc": now_iso(),
        "crm_destination": destination,
    }
    if existing is None:
        record["created_at_utc"] = record["updated_at_utc"]
        items.append(record)
        created = True
    else:
        record["created_at_utc"] = existing.get("created_at_utc", record["updated_at_utc"])
        existing.update(record)
        record = existing
        created = False
    write_json(path, store)
    return {"created": created, "record": record}


def stage_operator_response(
    *,
    idempotency_key: str,
    draft_body: str,
    channel: str = "email_or_ticket",
    auto_send: bool = False,
    responses_path: Path | None = None,
) -> dict[str, Any]:
    """Stage an operator reply. Auto-send to customers is refused."""
    if auto_send:
        raise PermissionError(
            "Automatic customer sends are refused; stage the draft and use an explicit send action."
        )
    if not (draft_body or "").strip():
        raise ValueError("Operator response draft must be non-empty.")
    # Never persist secrets-looking material markers; keep draft local and bounded.
    if len(draft_body) > 8000:
        raise ValueError("Operator response draft exceeds 8000 characters.")
    path = responses_path or OPERATOR_RESPONSES_PATH
    store = load_json(path, {"schema_version": 1, "items": []})
    items = store.setdefault("items", [])
    existing = next((item for item in items if item.get("idempotency_key") == idempotency_key), None)
    record = {
        "idempotency_key": idempotency_key,
        "channel": channel,
        "draft_body": draft_body.strip(),
        "status": "staged_awaiting_explicit_send",
        "auto_send": False,
        "sent": False,
        "updated_at_utc": now_iso(),
    }
    if existing is None:
        record["created_at_utc"] = record["updated_at_utc"]
        items.append(record)
        created = True
    else:
        record["created_at_utc"] = existing.get("created_at_utc", record["updated_at_utc"])
        existing.update(record)
        record = existing
        created = False
    write_json(path, store)
    return {"created": created, "record": record}


def local_fixture_transporter(entry: dict[str, Any]) -> dict[str, Any]:
    """Synthetic transporter: records local delivery only. Not a live CRM/Slack send."""
    if entry.get("crm_record", {}).get("status") == "skipped_consent":
        return {
            "ok": True,
            "live": False,
            "status": "suppressed_consent",
            "note": "LOCAL_FIXTURE_TRANSPORTER; consent skipped — nothing remote.",
        }
    return {
        "ok": True,
        "live": False,
        "status": "delivered_local_fixture",
        "note": "LOCAL_FIXTURE_TRANSPORTER; not a live CRM or Slack readback.",
        "crm_destination": entry.get("crm_record", {}).get("crm_destination"),
        "slack_channel_key": entry.get("slack", {}).get("channel_key"),
    }


def unavailable_live_transporter(entry: dict[str, Any]) -> dict[str, Any]:
    """Stand-in when live credentials are absent."""
    return {
        "ok": False,
        "live": False,
        "status": "provider_unavailable",
        "note": "Live commercial CRM/Slack credentials are not bound in this environment.",
    }


def deliver_outbox_once(
    *,
    outbox_path: Path | None = None,
    recovery_path: Path | None = None,
    transporter=None,
    max_attempts: int = 3,
) -> dict[str, Any]:
    """Deliver one pending outbox item with durable attempt counting (replay-safe)."""
    path = outbox_path or OUTBOX_PATH
    store = load_json(path, {"schema_version": 1, "items": []})
    items = store.setdefault("items", [])
    pending = next((item for item in items if item.get("status") == "pending_delivery"), None)
    if pending is None:
        return {"status": "idle", "delivered": False}
    transporter = transporter or local_fixture_transporter
    attempts = int(pending.get("attempts") or 0) + 1
    pending["attempts"] = attempts
    pending["updated_at_utc"] = now_iso()
    result = transporter(pending)
    if result.get("ok"):
        pending["status"] = result.get("status") or "delivered_local_fixture"
        pending["last_delivery"] = {k: v for k, v in result.items() if k != "secrets"}
        write_json(path, store)
        return {"status": pending["status"], "delivered": True, "entry": pending, "live": bool(result.get("live"))}
    reason = str(result.get("note") or result.get("status") or "delivery_failed")
    if attempts >= max_attempts:
        pending["status"] = "needs_recovery"
        enqueue_recovery(pending["idempotency_key"], reason, recovery_path=recovery_path)
    write_json(path, store)
    return {"status": pending["status"], "delivered": False, "entry": pending, "reason": reason}


def run_synthetic_inquiry_route(
    *,
    inquiry_reference: str,
    contact_fingerprint: str,
    order_reference: str | None = None,
    support_reference: str | None = None,
    outbox_path: Path | None = None,
    recovery_path: Path | None = None,
    support_path: Path | None = None,
    responses_path: Path | None = None,
    consent: str = "support_inquiry_only",
) -> dict[str, Any]:
    """Exercise inquiry → commercial CRM projection → Slack stage → optional support/response locally."""
    event = build_event(
        project_id="commercelint",
        event_type="inquiry.received",
        source_ref="synthetic_local_route",
        inquiry_reference=inquiry_reference,
        order_reference=order_reference,
        audience_consent_classification=consent,
        measurement_provenance="synthetic_fixture",
    )
    processed = process_customer_event(
        event, contact_fingerprint=contact_fingerprint, outbox_path=outbox_path
    )
    delivery = deliver_outbox_once(
        outbox_path=outbox_path,
        recovery_path=recovery_path,
        transporter=local_fixture_transporter,
    )
    support = None
    if support_reference:
        support = associate_order_support(
            inquiry_reference=inquiry_reference,
            order_reference=order_reference,
            support_reference=support_reference,
            support_path=support_path,
            note="Synthetic local association only.",
        )
    response = stage_operator_response(
        idempotency_key=event["idempotency_key"],
        draft_body=(
            f"Thanks for contacting CommerceLint about inquiry {inquiry_reference}. "
            "This staged reply was not sent to the customer."
        ),
        responses_path=responses_path,
    )
    destination = resolve_crm_destination("commercelint")
    return {
        "route": "inquiry->crm->slack->support->operator_response",
        "live_crm_or_slack": False,
        "fixture": True,
        "forbidden_primandir_portal": PRIMANDIR_PORTAL,
        "crm_destination": destination["crm_destination"],
        "event": event,
        "processed": processed,
        "delivery": {
            "status": delivery.get("status"),
            "delivered": delivery.get("delivered"),
            "live": delivery.get("live"),
        },
        "support": support,
        "operator_response": {
            "status": response["record"]["status"],
            "sent": response["record"]["sent"],
            "created": response["created"],
        },
        "replay_safe": True,
    }
