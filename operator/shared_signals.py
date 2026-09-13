#!/usr/bin/env python3
"""Bounded shared signals for CommerceLint and peer projects (W201).

Reuses existing CRM/run-log style records. Not a new orchestration framework.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIGNALS_PATH = ROOT / "state" / "shared_signals.json"
SUMMARY_PATH = ROOT / "state" / "business_summary.json"


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


def stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]


def empty_store() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at_utc": None,
        "actions": [],
        "outcomes": [],
        "source_inputs": [],
        "hypotheses": [],
    }


def upsert_by_id(items: list[dict[str, Any]], record: dict[str, Any], key: str = "id") -> bool:
    existing = next((item for item in items if item.get(key) == record[key]), None)
    if existing is None:
        items.append(record)
        return True
    existing.update(record)
    return False


def join_action_outcome(
    *,
    project_id: str,
    action_id: str,
    action_summary: str,
    outcome_status: str,
    source_coverage: list[str],
    measurement_provenance: str | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    path = store_path or SIGNALS_PATH
    store = load_json(path, empty_store())
    action = {
        "id": action_id,
        "project_id": project_id,
        "summary": action_summary,
        "source_coverage": source_coverage,
        "updated_at_utc": now_iso(),
    }
    outcome = {
        "id": f"out_{stable_id(action_id, outcome_status)}",
        "action_id": action_id,
        "project_id": project_id,
        "status": outcome_status,
        "measurement_provenance": measurement_provenance,
        "observed_at_utc": now_iso(),
    }
    upsert_by_id(store["actions"], action)
    upsert_by_id(store["outcomes"], outcome)
    store["updated_at_utc"] = now_iso()
    write_json(path, store)
    return {"action": action, "outcome": outcome}


def connect_source_input(
    *,
    project_id: str,
    source_name: str,
    metric_name: str,
    value: Any,
    observed_at_utc: str | None = None,
    changed_only: bool = True,
    store_path: Path | None = None,
) -> dict[str, Any]:
    path = store_path or SIGNALS_PATH
    store = load_json(path, empty_store())
    input_id = f"src_{stable_id(project_id, source_name, metric_name)}"
    previous = next((item for item in store["source_inputs"] if item.get("id") == input_id), None)
    if changed_only and previous is not None and previous.get("value") == value:
        return {"created": False, "changed": False, "record": previous}
    record = {
        "id": input_id,
        "project_id": project_id,
        "source_name": source_name,
        "metric_name": metric_name,
        "value": value,
        "observed_at_utc": observed_at_utc or now_iso(),
        "changed_from_previous": previous is not None and previous.get("value") != value,
    }
    upsert_by_id(store["source_inputs"], record)
    store["updated_at_utc"] = now_iso()
    write_json(path, store)
    return {"created": previous is None, "changed": True, "record": record}


def record_hypothesis_cycle(
    *,
    project_id: str,
    hypothesis: str,
    change: str,
    observation_window: str,
    decision: str,
    evidence: list[str],
    store_path: Path | None = None,
) -> dict[str, Any]:
    if decision not in {"continue", "revise", "stop", "inconclusive"}:
        raise ValueError("decision must be continue|revise|stop|inconclusive")
    path = store_path or SIGNALS_PATH
    store = load_json(path, empty_store())
    record = {
        "id": f"hyp_{stable_id(project_id, hypothesis, change)}",
        "project_id": project_id,
        "hypothesis": hypothesis,
        "change": change,
        "observation_window": observation_window,
        "decision": decision,
        "evidence": evidence,
        "recorded_at_utc": now_iso(),
    }
    upsert_by_id(store["hypotheses"], record)
    store["updated_at_utc"] = now_iso()
    write_json(path, store)
    return record


def build_business_summary(
    *,
    store_path: Path | None = None,
    summary_path: Path | None = None,
    extra_unknowns: list[str] | None = None,
) -> dict[str, Any]:
    store = load_json(store_path or SIGNALS_PATH, empty_store())
    unknowns = list(extra_unknowns or [])
    if not store.get("source_inputs"):
        unknowns.append("No connected source inputs yet.")
    paid = [item for item in store.get("outcomes", []) if item.get("status") == "paid_fulfilled"]
    summary = {
        "schema_version": 1,
        "generated_at_utc": now_iso(),
        "freshness_utc": store.get("updated_at_utc"),
        "projects_seen": sorted({item.get("project_id") for item in store.get("actions", []) if item.get("project_id")}),
        "action_count": len(store.get("actions", [])),
        "outcome_count": len(store.get("outcomes", [])),
        "source_input_count": len(store.get("source_inputs", [])),
        "hypothesis_count": len(store.get("hypotheses", [])),
        "paid_fulfilled_outcomes": len(paid),
        "unknowns": unknowns,
        "note": "Private summary artifact; not a revenue claim.",
    }
    write_json(summary_path or SUMMARY_PATH, summary)
    return summary


def evaluate_worker_controls(control: dict[str, Any], *, attempts: int = 0) -> dict[str, Any]:
    """Budget / no-op / retry / stop controls for existing workers."""
    mode = str(control.get("mode", "RUN")).upper()
    if mode == "STOP":
        return {"allow_action": False, "decision": "stop", "reason": "CONTROL mode is STOP"}
    if mode == "PAUSE":
        return {"allow_action": False, "decision": "no_op", "reason": "CONTROL mode is PAUSE"}
    if mode == "NO_OP":
        return {"allow_action": False, "decision": "no_op", "reason": "CONTROL mode is NO_OP"}
    budget = control.get("daily_action_budget")
    used = int(control.get("daily_actions_used") or 0)
    if budget is not None and used >= int(budget):
        return {"allow_action": False, "decision": "budget_exhausted", "reason": f"daily_action_budget {budget} reached"}
    max_retries = int(control.get("max_task_retries") or 3)
    if attempts > max_retries:
        return {"allow_action": False, "decision": "stop_retries", "reason": f"attempts {attempts} exceed max_task_retries {max_retries}"}
    return {"allow_action": True, "decision": "run", "reason": "controls permit one bounded action"}
