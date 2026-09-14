#!/usr/bin/env python3
"""Ingest verified CommerceLint deployment receipts into the durable run diary."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from typing import Any

from runlog import record_event, stable_event_id, workflow_run_url

RECEIPT_URL = (
    "https://raw.githubusercontent.com/pri8771/priyanshchordia.com/main/"
    "deployments/commercelint-production.json"
)
RUN_API = "https://api.github.com/repos/pri8771/priyanshchordia.com/actions/runs/{run_id}"
USER_AGENT = "CommerceLint-Deployment-Log-Sync/1.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_json(url: str, timeout: int = 20) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object from {url}")
    return payload


def run_metadata(receipt: dict[str, Any]) -> dict[str, Any]:
    run_url = str(receipt.get("workflow_run_url", ""))
    match = re.search(r"/actions/runs/(\d+)", run_url)
    if not match:
        return {}
    try:
        return fetch_json(RUN_API.format(run_id=match.group(1)))
    except Exception:
        return {}


def receipt_event(receipt: dict[str, Any], *, backfilled: bool = False) -> dict[str, Any]:
    metadata = run_metadata(receipt)
    verified_at = str(receipt.get("verified_at_utc") or now_iso())
    started_at = str(metadata.get("run_started_at") or metadata.get("created_at") or verified_at)
    ended_at = str(metadata.get("updated_at") or verified_at)
    run_url = str(receipt.get("workflow_run_url", ""))
    run_id_match = re.search(r"/actions/runs/(\d+)", run_url)
    run_id = run_id_match.group(1) if run_id_match else str(receipt.get("portfolio_commit") or verified_at)
    source_changed = bool(receipt.get("source_changed"))
    indexnow = receipt.get("indexnow", {}) if isinstance(receipt.get("indexnow"), dict) else {}
    indexnow_outcome = str(indexnow.get("outcome", "not_recorded"))
    checks = [
        {"name": f"deployment_check_{index + 1}", "ok": True, "detail": str(detail)}
        for index, detail in enumerate(receipt.get("checks", []))
    ]
    failures = []
    blockers = []
    if indexnow_outcome == "failure":
        failures.append("Production deployment passed, but the receipt records a failed IndexNow submission.")
        blockers.append("Search-discovery notification needs an automatic retry on the next changed release.")
    backfill_notes = []
    if not metadata:
        backfill_notes.append(
            "The deployment receipt did not expose a run-start timestamp through workflow metadata; the verified receipt timestamp was used for both start and end."
        )
    return {
        "event_id": stable_event_id("production_deployment", run_id),
        "run_id": run_id,
        "workflow": "production_deployment",
        "status": "success" if str(receipt.get("status")) == "live" else "failed",
        "started_at_utc": started_at,
        "ended_at_utc": ended_at,
        "trigger": metadata.get("event") or "not_recorded",
        "task_selected": {
            "id": "deploy-commerce-lint",
            "title": "Deploy and verify the latest CommerceLint release",
            "type": "deployment",
        },
        "decision_summary": (
            "The production workflow detected a changed CommerceLint source revision and deployed it."
            if source_changed
            else "The hourly production workflow verified and redeployed the current CommerceLint source revision."
        ),
        "evidence_consulted": [
            "pri8771/priyanshchordia.com deployment receipt",
            f"CommerceLint source revision {receipt.get('source_commit', 'not recorded')}",
            "Generated portfolio validation and public CommerceLint funnel checks",
        ],
        "action_taken": {
            "summary": f"Mounted CommerceLint at {receipt.get('url', 'the production URL')} and ran the production verification gate.",
            "details": [
                f"Source changed: {source_changed}",
                f"IndexNow outcome: {indexnow_outcome}; URLs: {indexnow.get('url_count', 0)}",
            ],
        },
        "verification": {
            "status": "passed" if str(receipt.get("status")) == "live" else "failed",
            "summary": f"Deployment receipt status is {receipt.get('status', 'not recorded')} at {verified_at}.",
            "checks": checks,
        },
        "metrics_before": {},
        "metrics_after": {
            "source_changed": source_changed,
            "indexnow_url_count": indexnow.get("url_count", 0),
        },
        "blockers": blockers,
        "failures_retries": failures,
        "lessons": [],
        "next_action": "Continue hourly deployment checks; the autonomous smoke monitor independently verifies the public funnel.",
        "links": [run_url, str(receipt.get("url", "")), str(receipt.get("scanner_url", ""))],
        "commit_hashes": [
            str(receipt.get("source_commit", "")),
            str(receipt.get("portfolio_commit", "")),
        ],
        "backfilled": backfilled,
        "backfill_notes": backfill_notes,
        "source": {
            "system": "production_deployment_receipt",
            "references": [RECEIPT_URL],
        },
    }


def sync_latest(*, backfilled: bool = False) -> tuple[dict[str, Any], bool]:
    receipt = fetch_json(RECEIPT_URL)
    return record_event(receipt_event(receipt, backfilled=backfilled))


def record_sync_failure(exc: Exception) -> None:
    timestamp = now_iso()
    run_id = os.environ.get("GITHUB_RUN_ID") or timestamp
    record_event({
        "event_id": stable_event_id("deployment_log_sync", run_id),
        "run_id": run_id,
        "workflow": "deployment_log_sync",
        "status": "failed",
        "started_at_utc": timestamp,
        "ended_at_utc": timestamp,
        "trigger": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "task_selected": {"id": "sync-deployment-receipt", "title": "Ingest the latest deployment receipt", "type": "documentation"},
        "decision_summary": "The durable diary must reconcile the external production deployment receipt into the CommerceLint source-of-truth repository.",
        "evidence_consulted": [RECEIPT_URL],
        "action_taken": {"summary": "The deployment receipt could not be ingested.", "details": []},
        "verification": {"status": "failed", "summary": f"{type(exc).__name__}: {exc}", "checks": []},
        "metrics_before": {},
        "metrics_after": {},
        "blockers": ["The latest external deployment receipt was temporarily unavailable or invalid."],
        "failures_retries": [f"{type(exc).__name__}: {exc}"],
        "lessons": [],
        "next_action": "Retry automatically during the next production-smoke cycle.",
        "links": [workflow_run_url() or "", RECEIPT_URL],
        "commit_hashes": [os.environ["GITHUB_SHA"]] if os.environ.get("GITHUB_SHA") else [],
        "source": {"system": "deployment_log_sync", "references": [RECEIPT_URL]},
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest the latest verified CommerceLint deployment receipt.")
    parser.add_argument("--backfilled", action="store_true", help="Mark the ingested receipt as historical backfill.")
    args = parser.parse_args()
    try:
        event, appended = sync_latest(backfilled=args.backfilled)
        print(json.dumps({"event_id": event["event_id"], "appended": appended}, sort_keys=True))
        return 0
    except Exception as exc:
        record_sync_failure(exc)
        print(f"Deployment receipt sync failed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
