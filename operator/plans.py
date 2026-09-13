#!/usr/bin/env python3
"""Authoritative CommerceLint paid-plan contract."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLANS_PATH = ROOT / "config" / "plans.json"

ALLOWED_PLAN_IDS = ("sample", "lite", "comprehensive")


def load_plans_config(path: Path | None = None) -> dict[str, Any]:
    payload = json.loads((path or PLANS_PATH).read_text(encoding="utf-8"))
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("Unsupported plans schema_version.")
    plans = payload.get("plans")
    if not isinstance(plans, dict):
        raise ValueError("plans must be an object.")
    for plan_id in ALLOWED_PLAN_IDS:
        if plan_id not in plans:
            raise ValueError(f"Missing required plan: {plan_id}")
    return payload


def get_plan(plan_id: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config or load_plans_config()
    key = str(plan_id or "").strip().lower()
    plan = payload["plans"].get(key)
    if not plan:
        raise ValueError(f"Unknown plan_id: {plan_id!r}. Allowed: {', '.join(ALLOWED_PLAN_IDS)}.")
    return dict(plan)


def money_usd(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Invalid USD amount: {value!r}") from exc
    if amount < 0:
        raise ValueError("USD amounts cannot be negative.")
    return amount.quantize(Decimal("0.01"))


def assert_plan_price(plan_id: str, claimed_price: Any, config: dict[str, Any] | None = None) -> Decimal:
    plan = get_plan(plan_id, config)
    expected = money_usd(plan["price_usd"])
    claimed = money_usd(claimed_price)
    if claimed != expected:
        raise ValueError(
            f"Plan {plan['id']} price must be {expected} USD; browser-supplied {claimed} is rejected."
        )
    return expected


def plan_public_js(config: dict[str, Any] | None = None) -> str:
    payload = config or load_plans_config()
    public = {
        plan_id: {
            "name": plan["name"],
            "price": f"{money_usd(plan['price_usd']):.2f}",
            "maxPublicUrls": int(plan["max_public_product_urls"]),
        }
        for plan_id, plan in payload["plans"].items()
    }
    return "window.commerceLintPlans = Object.freeze(" + json.dumps(public, separators=(",", ": ")) + ");\n"
