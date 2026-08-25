#!/usr/bin/env python3
"""Privacy-safe operational CRM for public CommerceLint lead references.

Git is public, so this ledger deliberately excludes email addresses, private
messages, free-text notes, and unpublished customer information. Those fields
belong only in the private CommerceLint CRM sheet.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ALLOWED_STAGES = {
    "needs_public_url",
    "new",
    "qualified",
    "contacted",
    "scope_confirmed",
    "payment_requested",
    "won",
    "lost",
}
PRIVATE_FIELD_NAMES = {
    "email",
    "contact_email",
    "context",
    "notes",
    "private_notes",
    "message_body",
}


def empty_crm() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at_utc": None,
        "leads": [],
        "activities": [],
    }


def _public_lead(payload: dict[str, Any], at_utc: str, existing: dict[str, Any] | None) -> dict[str, Any]:
    qualified = bool(payload.get("qualified"))
    proposed_stage = "new" if qualified else "needs_public_url"
    current_stage = str((existing or {}).get("stage") or proposed_stage)
    if current_stage == "needs_public_url" and qualified:
        current_stage = "new"
    return {
        "id": str(payload["id"]),
        "record_type": "lead",
        "source": "github_issue_form",
        "public_reference": str(payload.get("issue_url") or ""),
        "public_contact_handle": str(payload.get("github_user") or "unknown"),
        "created_at_utc": str((existing or {}).get("created_at_utc") or payload.get("created_at_utc") or at_utc),
        "updated_at_utc": at_utc,
        "last_activity_at_utc": str((existing or {}).get("last_activity_at_utc") or at_utc),
        "stage": current_stage,
        "qualified": qualified,
        "owner": str((existing or {}).get("owner") or "Priyansh Chordia"),
        "potential_value_usd": int((existing or {}).get("potential_value_usd") or (49 if qualified else 0)),
        "currency": "USD",
        "store_url": str(payload.get("store_url") or ""),
        "role": str(payload.get("role") or ""),
        "platform": str(payload.get("platform") or ""),
        "primary_need": str(payload.get("main_goal") or ""),
        "next_action": str(
            (existing or {}).get("next_action")
            or ("Review first pass and confirm scope" if qualified else "Await a corrected public URL")
        ),
        "next_action_due_utc": (existing or {}).get("next_action_due_utc"),
        "privacy_classification": "public_source_only",
    }


def upsert_public_github_lead(
    crm: dict[str, Any], payload: dict[str, Any], *, at_utc: str
) -> tuple[dict[str, Any], bool]:
    """Idempotently project one public GitHub request into the CRM."""

    lead_id = str(payload["id"])
    leads = crm.setdefault("leads", [])
    existing = next((item for item in leads if item.get("id") == lead_id), None)
    record = _public_lead(payload, at_utc, existing)
    is_new = existing is None
    changed = is_new
    if existing is None:
        leads.append(record)
        activity_id = f"{lead_id}:created"
        if not any(item.get("id") == activity_id for item in crm.setdefault("activities", [])):
            crm["activities"].append(
                {
                    "id": activity_id,
                    "lead_id": lead_id,
                    "activity_type": "lead_created",
                    "at_utc": at_utc,
                    "from_stage": None,
                    "to_stage": record["stage"],
                    "public_reference": record["public_reference"],
                }
            )
    else:
        record["updated_at_utc"] = str(existing.get("updated_at_utc") or at_utc)
        record["last_activity_at_utc"] = str(existing.get("last_activity_at_utc") or at_utc)
        changed = any(existing.get(key) != value for key, value in record.items())
        if changed:
            record["updated_at_utc"] = at_utc
        existing.update(record)
        record = existing
    crm["schema_version"] = SCHEMA_VERSION
    crm["updated_at_utc"] = at_utc if is_new or changed else crm.get("updated_at_utc")
    validate_crm(crm)
    return record, is_new


def validate_crm(crm: dict[str, Any]) -> None:
    if crm.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported CRM schema version.")
    lead_ids: set[str] = set()
    for lead in crm.get("leads", []):
        lead_id = str(lead.get("id") or "")
        if not lead_id or lead_id in lead_ids:
            raise ValueError("CRM lead IDs must be non-empty and unique.")
        lead_ids.add(lead_id)
        if lead.get("stage") not in ALLOWED_STAGES:
            raise ValueError(f"Unsupported CRM stage for {lead_id}: {lead.get('stage')}")
        forbidden = PRIVATE_FIELD_NAMES.intersection(lead)
        if forbidden:
            raise ValueError(f"Private fields are not allowed in public CRM records: {sorted(forbidden)}")
        if lead.get("privacy_classification") != "public_source_only":
            raise ValueError(f"CRM lead {lead_id} is not marked public-source-only.")
    activity_ids = [str(item.get("id") or "") for item in crm.get("activities", [])]
    if len(activity_ids) != len(set(activity_ids)) or any(not value for value in activity_ids):
        raise ValueError("CRM activity IDs must be non-empty and unique.")


def summary(crm: dict[str, Any]) -> dict[str, Any]:
    validate_crm(crm)
    by_stage = {stage: 0 for stage in sorted(ALLOWED_STAGES)}
    potential_value = 0
    for lead in crm.get("leads", []):
        by_stage[lead["stage"]] += 1
        if lead["stage"] not in {"won", "lost"}:
            potential_value += int(lead.get("potential_value_usd") or 0)
    return {
        "lead_count": len(crm.get("leads", [])),
        "open_potential_value_usd": potential_value,
        "by_stage": by_stage,
        "updated_at_utc": crm.get("updated_at_utc"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "summary"))
    parser.add_argument("--path", type=Path, default=Path("state/crm.json"))
    args = parser.parse_args()
    crm = json.loads(args.path.read_text(encoding="utf-8"))
    validate_crm(crm)
    if args.command == "summary":
        print(json.dumps(summary(crm), indent=2, sort_keys=True))
    else:
        print(f"CRM validation passed: {len(crm.get('leads', []))} public lead record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
