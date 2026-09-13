#!/usr/bin/env python3
"""Private CommerceLint intake: validate plan/URLs before any charge path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .plans import assert_plan_price, get_plan, load_plans_config
    from .public_url import validate_url_batch
except ImportError:
    from plans import assert_plan_price, get_plan, load_plans_config
    from public_url import validate_url_batch

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_INTAKE_PATH = ROOT / "state" / "private_intake_public.json"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def email_fingerprint(email: str) -> str:
    normalized = email.strip().lower()
    return hashlib.sha256(f"commercelint-intake:{normalized}".encode("utf-8")).hexdigest()


def private_store_path() -> Path | None:
    raw = os.environ.get("COMMERCELINT_PRIVATE_INTAKE_PATH", "").strip()
    return Path(raw) if raw else None


def validate_intake_request(
    *,
    plan_id: str,
    urls: list[str] | str,
    contact_email: str,
    claimed_price: Any | None = None,
    resolve_dns: bool = True,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate private intake. charge_allowed is False until plan+URLs+email pass."""
    payload = config or load_plans_config()
    try:
        plan = get_plan(plan_id, payload)
    except ValueError as exc:
        return {
            "ok": False,
            "charge_allowed": False,
            "status": "rejected_plan",
            "error": str(exc),
            "plan": None,
            "urls": {"accepted_urls": [], "rejected": [], "ok": False},
        }

    price = None
    if claimed_price is not None:
        try:
            price = assert_plan_price(plan_id, claimed_price, payload)
        except ValueError as exc:
            return {
                "ok": False,
                "charge_allowed": False,
                "status": "rejected_price",
                "error": str(exc),
                "plan": plan,
                "urls": {"accepted_urls": [], "rejected": [], "ok": False},
            }
    else:
        from decimal import Decimal

        price = Decimal(str(plan["price_usd"])).quantize(Decimal("0.01"))

    email = (contact_email or "").strip()
    if not email or not EMAIL_RE.match(email):
        return {
            "ok": False,
            "charge_allowed": False,
            "status": "rejected_email",
            "error": "A valid delivery email is required before charging.",
            "plan": plan,
            "urls": {"accepted_urls": [], "rejected": [], "ok": False},
        }

    batch = validate_url_batch(
        urls,
        max_urls=int(plan["max_public_product_urls"]),
        resolve_dns=resolve_dns,
    )
    if not batch["ok"]:
        return {
            "ok": False,
            "charge_allowed": False,
            "status": "rejected_urls",
            "error": batch["error"],
            "plan": plan,
            "urls": batch,
            "remedy": "Correct or remove unsupported URLs, stay within the plan page limit, then resubmit. No charge is created for rejected intake.",
        }

    inquiry_id = hashlib.sha256(
        json.dumps(
            {
                "plan": plan["id"],
                "urls": batch["accepted_urls"],
                "email_fp": email_fingerprint(email),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:24]

    return {
        "ok": True,
        "charge_allowed": True,
        "status": "validated_pending_payment",
        "error": None,
        "inquiry_id": f"inq_{inquiry_id}",
        "plan": plan,
        "price_usd": float(price),
        "urls": batch,
        "contact_email_fingerprint": email_fingerprint(email),
        "crm_project_id": "commercelint",
        "forbidden_crm": list(payload.get("crm_destination_policy", {}).get("forbidden_destinations") or []),
    }


def record_validated_intake(
    result: dict[str, Any],
    *,
    source: str = "private_web_form",
    public_path: Path | None = None,
) -> dict[str, Any]:
    if not result.get("ok"):
        raise ValueError("Refusing to record an invalid intake as chargeable.")

    at = now_iso()
    public_record = {
        "inquiry_id": result["inquiry_id"],
        "project_id": "commercelint",
        "source": source,
        "plan_id": result["plan"]["id"],
        "price_usd": result["price_usd"],
        "accepted_url_count": len(result["urls"]["accepted_urls"]),
        "accepted_urls": result["urls"]["accepted_urls"],
        "contact_email_fingerprint": result["contact_email_fingerprint"],
        "status": result["status"],
        "charge_allowed": True,
        "created_at_utc": at,
        "updated_at_utc": at,
    }

    path = public_path or PUBLIC_INTAKE_PATH
    store = load_json(path, {"schema_version": 1, "updated_at_utc": None, "inquiries": []})
    inquiries = store.setdefault("inquiries", [])
    existing = next((item for item in inquiries if item.get("inquiry_id") == public_record["inquiry_id"]), None)
    if existing is None:
        inquiries.append(public_record)
    else:
        public_record["created_at_utc"] = existing.get("created_at_utc", at)
        existing.update(public_record)
        public_record = existing
    store["updated_at_utc"] = at
    write_json(path, store)

    private_path = private_store_path()
    if private_path is not None:
        private_store = load_json(private_path, {"schema_version": 1, "inquiries": []})
        # Private store may hold delivery email when operator configures a non-repo path.
        # This module never writes private email into the git-tracked public projection.
        private_store.setdefault("inquiries", []).append(
            {
                **public_record,
                "note": "Delivery email must be supplied by the calling runtime into this private path only.",
            }
        )
        write_json(private_path, private_store)

    return public_record


def corrected_url_followup(
    previous: dict[str, Any],
    *,
    new_urls: list[str] | str,
    resolve_dns: bool = True,
) -> dict[str, Any]:
    """Re-validate a previously rejected intake after the customer supplies corrected URLs."""
    if previous.get("status") not in {"rejected_urls", "needs_public_url", "rejected_plan", "validated_pending_payment"}:
        # Still allow revalidation for known prior rejection statuses and pending records.
        pass
    plan_id = (previous.get("plan") or {}).get("id") or previous.get("plan_id")
    email_fp = previous.get("contact_email_fingerprint")
    if not plan_id:
        return {"ok": False, "charge_allowed": False, "error": "Previous intake is missing plan_id."}
    # Email is already fingerprinted; caller must re-supply email for a full validate when creating charge.
    plan = get_plan(plan_id)
    batch = validate_url_batch(
        new_urls,
        max_urls=int(plan["max_public_product_urls"]),
        resolve_dns=resolve_dns,
    )
    if not batch["ok"]:
        return {
            "ok": False,
            "charge_allowed": False,
            "status": "rejected_urls",
            "error": batch["error"],
            "urls": batch,
            "previous_inquiry_id": previous.get("inquiry_id"),
            "remedy": "Provide corrected public product URLs within the plan limit before payment.",
        }
    return {
        "ok": True,
        "charge_allowed": bool(email_fp),
        "status": "urls_corrected_pending_payment" if email_fp else "urls_corrected_need_email",
        "plan": plan,
        "urls": batch,
        "previous_inquiry_id": previous.get("inquiry_id"),
        "contact_email_fingerprint": email_fp,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CommerceLint private intake before charging.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--claimed-price", default=None)
    parser.add_argument("--no-dns", action="store_true")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--public-out", type=Path, default=None)
    args = parser.parse_args()

    result = validate_intake_request(
        plan_id=args.plan,
        urls=args.url,
        contact_email=args.email,
        claimed_price=args.claimed_price,
        resolve_dns=not args.no_dns,
    )
    if args.record and result.get("ok"):
        record = record_validated_intake(result, public_path=args.public_out)
        result = {**result, "recorded": record}
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
