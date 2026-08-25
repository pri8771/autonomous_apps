#!/usr/bin/env python3
"""Evaluate and durably document the independent CommerceLint heartbeat watchdog."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runlog import record_event, stable_event_id, workflow_run_url

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "state.json"
CONFIG_PATH = ROOT / "config" / "business.json"
RECEIPT_PATH = ROOT / "state" / "watchdog.json"


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def evaluate() -> dict[str, Any]:
    state = load_json(STATE_PATH)
    config = load_json(CONFIG_PATH)
    threshold = int(config.get("operating_policy", {}).get("heartbeat_stale_minutes", 75))
    value = state.get("operator", {}).get("last_success_at_utc")
    now = now_utc()
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    stale = True
    age_minutes = 999999
    missed_current_hour = False
    reason = "no successful heartbeat exists"
    if value:
        last = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        age_minutes = int((now - last).total_seconds() / 60)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        last_hour = last.replace(minute=0, second=0, microsecond=0)
        missed_current_hour = event_name == "schedule" and last_hour < current_hour
        stale = age_minutes > threshold or missed_current_hour
        if missed_current_hour:
            reason = "no successful operator cycle was recorded in the current UTC hour"
        elif age_minutes > threshold:
            reason = f"heartbeat exceeded the {threshold}-minute age threshold"
        else:
            reason = "heartbeat is current"
    return {
        "evaluated_at_utc": iso(now),
        "last_success_at_utc": value,
        "stale": stale,
        "age_minutes": age_minutes,
        "threshold_minutes": threshold,
        "missed_current_hour": missed_current_hour,
        "reason": reason,
    }


def write_outputs(result: dict[str, Any]) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with open(output, "a", encoding="utf-8") as handle:
        handle.write(f"stale={'true' if result['stale'] else 'false'}\n")
        handle.write(f"age_minutes={result['age_minutes']}\n")
        handle.write(f"threshold_minutes={result['threshold_minutes']}\n")
        handle.write(f"reason={result['reason']}\n")
        handle.write(f"started_at_utc={result['evaluated_at_utc']}\n")
        handle.write(f"last_success_at_utc={result.get('last_success_at_utc') or ''}\n")


def record(result: dict[str, Any], recovery_outcome: str) -> tuple[dict[str, Any], bool]:
    ended_at = iso(now_utc())
    run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{result['evaluated_at_utc']}"
    stale = bool(result["stale"])
    recovery_attempted = stale
    recovery_accepted = recovery_outcome == "success"
    status = "failed" if stale and not recovery_accepted else "success"
    action = (
        "Dispatched the hourly operator recovery workflow."
        if recovery_attempted and recovery_accepted
        else "Attempted to dispatch recovery, but GitHub did not accept the dispatch."
        if recovery_attempted
        else "No recovery dispatch was necessary."
    )
    verification_summary = (
        "The heartbeat was within policy."
        if not stale
        else "GitHub accepted the recovery dispatch; a later heartbeat verifies recovery completion."
        if recovery_accepted
        else "The stale heartbeat remains unresolved because recovery dispatch failed."
    )
    receipt = {
        "schema_version": 1,
        **result,
        "recorded_at_utc": ended_at,
        "recovery_attempted": recovery_attempted,
        "recovery_outcome": recovery_outcome,
        "workflow_run": workflow_run_url(),
    }
    write_json(RECEIPT_PATH, receipt)
    source_sha = os.environ.get("GITHUB_SHA", "").strip()
    return record_event({
        "event_id": stable_event_id("watchdog", run_id),
        "run_id": run_id,
        "workflow": "watchdog",
        "status": status,
        "started_at_utc": result["evaluated_at_utc"],
        "ended_at_utc": ended_at,
        "trigger": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "task_selected": {
            "id": "recover-stale-heartbeat" if stale else "verify-heartbeat",
            "title": "Dispatch operator recovery" if stale else "Verify the operator heartbeat",
            "type": "recovery" if stale else "monitoring",
        },
        "decision_summary": (
            f"Recovery was selected because {result['reason']}."
            if stale
            else f"No recovery was selected because {result['reason']}."
        ),
        "evidence_consulted": [
            "state/state.json operator.last_success_at_utc",
            "config/business.json operating_policy.heartbeat_stale_minutes",
            f"Heartbeat age {result['age_minutes']} minutes against threshold {result['threshold_minutes']} minutes",
        ],
        "action_taken": {"summary": action, "details": []},
        "verification": {
            "status": "passed" if status == "success" else "failed",
            "summary": verification_summary,
            "checks": [
                {
                    "name": "heartbeat_freshness",
                    "ok": not stale,
                    "detail": result["reason"],
                },
                {
                    "name": "recovery_dispatch",
                    "ok": recovery_accepted if stale else True,
                    "detail": recovery_outcome if stale else "not required",
                },
            ],
        },
        "metrics_before": {
            "heartbeat_age_minutes": result["age_minutes"],
            "heartbeat_threshold_minutes": result["threshold_minutes"],
        },
        "metrics_after": {
            "heartbeat_age_minutes": result["age_minutes"],
            "recovery_dispatch_accepted": recovery_accepted,
        },
        "blockers": ([] if status == "success" else ["Operator recovery dispatch failed."]),
        "failures_retries": ([] if status == "success" else [f"Recovery dispatch outcome: {recovery_outcome}"]),
        "lessons": ([] if stale else ["The independent heartbeat remained within the configured policy at evaluation time."]),
        "next_action": (
            "Verify that a subsequent operator heartbeat completes the recovery."
            if stale and recovery_accepted
            else "Continue independent hourly heartbeat checks."
            if not stale
            else "Open the stale-heartbeat incident and retry recovery."
        ),
        "links": [workflow_run_url() or ""],
        "commit_hashes": [source_sha] if source_sha else [],
        "source": {"system": "watchdog_runtime", "references": ["state/watchdog.json", "state/state.json"]},
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate or record the CommerceLint heartbeat watchdog.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("evaluate")
    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--stale", required=True, choices=("true", "false"))
    record_parser.add_argument("--age-minutes", required=True, type=int)
    record_parser.add_argument("--threshold-minutes", required=True, type=int)
    record_parser.add_argument("--reason", required=True)
    record_parser.add_argument("--started-at-utc", required=True)
    record_parser.add_argument("--last-success-at-utc", default="")
    record_parser.add_argument("--recovery-outcome", required=True)
    args = parser.parse_args()

    if args.command == "evaluate":
        result = evaluate()
        write_outputs(result)
        print(
            f"Heartbeat age={result['age_minutes']} minutes; threshold={result['threshold_minutes']}; "
            f"stale={result['stale']}; reason={result['reason']}"
        )
        return 0
    result = {
        "evaluated_at_utc": args.started_at_utc,
        "last_success_at_utc": args.last_success_at_utc or None,
        "stale": args.stale == "true",
        "age_minutes": args.age_minutes,
        "threshold_minutes": args.threshold_minutes,
        "missed_current_hour": "current UTC hour" in args.reason,
        "reason": args.reason,
    }
    event, appended = record(result, args.recovery_outcome)
    print(json.dumps({"event_id": event["event_id"], "appended": appended}, sort_keys=True))
    return 0 if event["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
