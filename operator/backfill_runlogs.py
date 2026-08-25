#!/usr/bin/env python3
"""Backfill the CommerceLint audit diary from retained evidence without invention."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from deployment_log_sync import receipt_event
from runlog import UNKNOWN, record_events, stable_event_id

ROOT = Path(__file__).resolve().parents[1]


def command_json(args: list[str]) -> Any:
    result = subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def git_text(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=True)
    return result.stdout


def git_json_at(revision: str, path: str) -> dict[str, Any]:
    try:
        payload = git_text("show", f"{revision}:{path}")
        value = json.loads(payload)
        return value if isinstance(value, dict) else {}
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}


def metrics_at(revision: str) -> dict[str, Any]:
    state = git_json_at(revision, "state/state.json")
    metrics = state.get("metrics", {}) if isinstance(state, dict) else {}
    return dict(metrics) if isinstance(metrics, dict) else {}


def line_commits(path: Path) -> list[str]:
    relative = str(path.relative_to(ROOT))
    output = git_text("blame", "--line-porcelain", "--", relative)
    commits = []
    for line in output.splitlines():
        match = re.match(r"^\^?([0-9a-f]{40}) \d+ \d+(?: \d+)?$", line)
        if match:
            commits.append(match.group(1))
    return commits


def introducing_commit(path: str, marker: str) -> str | None:
    try:
        output = git_text("log", "--reverse", "--format=%H", f"-S{marker}", "--", path)
    except subprocess.CalledProcessError:
        return None
    return next((line.strip() for line in output.splitlines() if line.strip()), None)


def run_id_from_url(url: str) -> str | None:
    match = re.search(r"/actions/runs/(\d+)", url)
    return match.group(1) if match else None


def github_run_metadata(url: str, repository: str) -> dict[str, Any]:
    run_id = run_id_from_url(url)
    if not run_id:
        return {}
    try:
        value = command_json(["gh", "api", f"repos/{repository}/actions/runs/{run_id}"])
        return value if isinstance(value, dict) else {}
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}


def operator_events() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for path in sorted((ROOT / "state" / "runs").glob("????-??-??.jsonl")):
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        commits = line_commits(path)
        for line_number, line in enumerate(lines, start=1):
            legacy = json.loads(line)
            commit = commits[line_number - 1] if line_number <= len(commits) else None
            major = legacy.get("major_action", {}) if isinstance(legacy.get("major_action"), dict) else {}
            task_id = major.get("task_id")
            title = str(major.get("title") or "No task recorded")
            action_ok = bool(major.get("ok"))
            checks = legacy.get("checks", []) if isinstance(legacy.get("checks"), list) else []
            failed_checks = [item for item in checks if isinstance(item, dict) and not item.get("ok")]
            failures = []
            if legacy.get("error"):
                failures.append(str(legacy["error"]))
            failures.extend(f"{item.get('name', 'check')}: {item.get('detail', 'failed')}" for item in failed_checks)
            if not action_ok:
                failures.append(str(major.get("detail") or "Selected action failed."))
            if task_id:
                decision = (
                    f"The retained operator event records '{title}' as the selected major action. "
                    "The exact historical score comparison was not stored."
                )
            else:
                decision = (
                    "The retained event records a no-op after health checks; no eligible task or exact "
                    "historical score comparison was stored in that event."
                )
            notes = [
                "The historical event did not retain a run-specific next action or complete task-ranking comparison.",
                "The workflow start/end timestamps and action/check results come directly from the legacy JSONL event.",
            ]
            before = metrics_at(f"{commit}^") if commit else {}
            after = metrics_at(commit) if commit else {}
            if not before and not after:
                notes.append("No commit-linked before/after metrics snapshot could be recovered.")
            event = {
                "event_id": stable_event_id("hourly_operator", str(legacy.get("run_id"))),
                "run_id": legacy.get("run_id"),
                "workflow": "hourly_operator",
                "status": "success" if legacy.get("success") else "failed",
                "started_at_utc": legacy.get("started_at_utc"),
                "ended_at_utc": legacy.get("completed_at_utc") or legacy.get("started_at_utc"),
                "trigger": legacy.get("trigger") or "not_recorded",
                "task_selected": {"id": task_id, "title": title, "type": None},
                "decision_summary": decision,
                "evidence_consulted": [
                    f"{path.relative_to(ROOT)} line {line_number}",
                    *[f"{item.get('name', 'check')}: {item.get('detail', '')}" for item in checks if isinstance(item, dict)],
                ],
                "action_taken": {
                    "summary": str(major.get("detail") or UNKNOWN),
                    "details": [
                        str(value)
                        for value in (legacy.get("daily_review"), legacy.get("weekly_review"))
                        if value
                    ],
                },
                "verification": {
                    "status": "passed" if legacy.get("success") and action_ok else "failed",
                    "summary": f"{sum(bool(item.get('ok')) for item in checks if isinstance(item, dict))} of {len(checks)} recorded health checks passed; selected action passed: {action_ok}.",
                    "checks": checks,
                },
                "metrics_before": before,
                "metrics_after": after,
                "blockers": [],
                "failures_retries": failures,
                "lessons": [],
                "next_action": UNKNOWN,
                "links": ["https://priyanshchordia.com/commercelint/"],
                "commit_hashes": [commit] if commit else [],
                "backfilled": True,
                "backfill_notes": notes,
                "source": {"system": "legacy_operator_jsonl", "references": [f"{path.relative_to(ROOT)}:{line_number}"]},
            }
            output.append(event)
    return output


def growth_events() -> list[dict[str, Any]]:
    state = json.loads((ROOT / "state" / "growth_state.json").read_text(encoding="utf-8"))
    history = state.get("history", [])
    output = []
    previous: dict[str, Any] = {}
    for entry in history:
        timestamp = str(entry["at_utc"])
        commit = introducing_commit("state/growth_state.json", timestamp)
        output.append({
            "event_id": stable_event_id("growth_planner", "backfill", timestamp),
            "run_id": f"backfill-{timestamp}",
            "workflow": "growth_planner",
            "status": "success",
            "started_at_utc": timestamp,
            "ended_at_utc": timestamp,
            "trigger": "not_recorded",
            "task_selected": {"id": "refresh-acquisition-runway", "title": "Refresh the acquisition and content runway", "type": "growth_planning"},
            "decision_summary": "The retained planner history proves that the acquisition/content runway was refreshed; a run-specific selection rationale was not stored.",
            "evidence_consulted": ["state/growth_state.json retained history", "content/queue.json was the planner's durable backlog"],
            "action_taken": {
                "summary": f"Added {entry.get('added_content_items', 0)} items; recorded {entry.get('queued_content_items', 0)} queued and {entry.get('published_content_items', 0)} published items.",
                "details": [f"Patched {item}" for item in entry.get("patched_files", [])],
            },
            "verification": {"status": "passed", "summary": "The run result is present in the durable growth-state history.", "checks": []},
            "metrics_before": {
                "content_queued": previous.get("queued_content_items"),
                "content_published": previous.get("published_content_items"),
            } if previous else {},
            "metrics_after": {
                "content_added_this_run": entry.get("added_content_items", 0),
                "content_queued": entry.get("queued_content_items", 0),
                "content_published": entry.get("published_content_items", 0),
            },
            "blockers": [],
            "failures_retries": [],
            "lessons": [],
            "next_action": "Hand the refreshed backlog to the hourly operator; the exact historical handoff outcome was not retained.",
            "links": [],
            "commit_hashes": [commit] if commit else [],
            "backfilled": True,
            "backfill_notes": [
                "The retained history stored one timestamp rather than distinct start/end timestamps, so that exact timestamp is used for both.",
                "The trigger and run-specific blockers, lessons, and selection comparison were not retained.",
            ],
            "source": {"system": "growth_state_history", "references": ["state/growth_state.json"]},
        })
        previous = entry
    return output


def receipt_history(path: str) -> list[tuple[str, dict[str, Any]]]:
    commits = [line for line in git_text("log", "--reverse", "--format=%H", "--", path).splitlines() if line]
    history = []
    seen = set()
    for commit in commits:
        payload = git_json_at(commit, path)
        timestamp = payload.get("verified_at_utc")
        if payload and timestamp and timestamp not in seen:
            seen.add(timestamp)
            history.append((commit, payload))
    return history


def smoke_events() -> list[dict[str, Any]]:
    output = []
    for commit, receipt in receipt_history("state/production_smoke.json"):
        run_url = str(receipt.get("workflow_run", ""))
        metadata = github_run_metadata(run_url, "pri8771/autonomous_apps")
        timestamp = str(receipt["verified_at_utc"])
        run_id = run_id_from_url(run_url) or f"backfill-{timestamp}"
        checks_by_name = receipt.get("checks", {}) if isinstance(receipt.get("checks"), dict) else {}
        checks = [
            {"name": name, "ok": bool(value.get("ok")), "detail": str(value.get("detail", "")), "latency_ms": value.get("latency_ms")}
            for name, value in checks_by_name.items()
        ]
        failures = [str(item) for item in receipt.get("failures", [])]
        output.append({
            "event_id": stable_event_id("production_smoke", run_id),
            "run_id": run_id,
            "workflow": "production_smoke",
            "status": "success" if receipt.get("status") == "healthy" else "failed",
            "started_at_utc": metadata.get("run_started_at") or metadata.get("created_at") or timestamp,
            "ended_at_utc": metadata.get("updated_at") or timestamp,
            "trigger": metadata.get("event") or "not_recorded",
            "task_selected": {"id": "verify-production", "title": "Verify the public CommerceLint funnel", "type": "monitoring"},
            "decision_summary": "The retained production receipt proves an independent funnel and privacy smoke check; a run-specific rationale was not stored.",
            "evidence_consulted": [f"{name}: {value.get('url')} — {value.get('detail')}" for name, value in checks_by_name.items()],
            "action_taken": {"summary": f"Verified {len(checks)} production surfaces.", "details": []},
            "verification": {"status": "passed" if not failures else "failed", "summary": f"Receipt status: {receipt.get('status')}", "checks": checks},
            "metrics_before": metrics_at(f"{commit}^"),
            "metrics_after": metrics_at(commit),
            "blockers": failures,
            "failures_retries": failures,
            "lessons": [],
            "next_action": "Continue independent production monitoring.",
            "links": [run_url, str(receipt.get("production_base", ""))],
            "commit_hashes": [commit, str(receipt.get("immutable_action_sha", ""))],
            "backfilled": True,
            "backfill_notes": [
                "Per-attempt retry details were not retained in the historical receipt.",
                *( [] if metadata else ["Workflow metadata was unavailable; the exact receipt timestamp is used for both start and end."] ),
            ],
            "source": {"system": "production_smoke_git_history", "references": ["state/production_smoke.json"]},
        })
    return output


def indexnow_events() -> list[dict[str, Any]]:
    state = json.loads((ROOT / "state" / "indexnow_state.json").read_text(encoding="utf-8"))
    output = []
    for entry in state.get("history", []):
        timestamp = str(entry["at_utc"])
        commit = introducing_commit("state/indexnow_state.json", timestamp)
        accepted = bool(entry.get("accepted"))
        attempts = int(entry.get("attempts", 0))
        output.append({
            "event_id": stable_event_id("indexnow", "backfill", timestamp, str(entry.get("fingerprint", ""))[:12]),
            "run_id": f"backfill-{timestamp}",
            "workflow": "indexnow_notification",
            "status": "success" if accepted else "failed",
            "started_at_utc": timestamp,
            "ended_at_utc": timestamp,
            "trigger": "not_recorded",
            "task_selected": {"id": "notify-search-engines", "title": "Submit changed CommerceLint URLs to IndexNow", "type": "distribution"},
            "decision_summary": "The retained state proves a bounded changed-URL or full-sitemap IndexNow submission; the exact workflow trigger was not stored.",
            "evidence_consulted": [*entry.get("urls", []), str(entry.get("key_location", ""))],
            "action_taken": {"summary": f"Submitted {entry.get('url_count', 0)} CommerceLint URLs to IndexNow.", "details": []},
            "verification": {"status": "passed" if accepted else "failed", "summary": f"Accepted: {accepted}; HTTP status: {entry.get('http_status')}", "checks": []},
            "metrics_before": {},
            "metrics_after": {"submitted_url_count": entry.get("url_count", 0), "http_status": entry.get("http_status")},
            "blockers": [] if accepted else ["IndexNow did not accept the submission."],
            "failures_retries": ([] if accepted and attempts <= 1 else [f"Submission attempts: {attempts}"]),
            "lessons": [],
            "next_action": "Submit again only after a changed release or an explicit full-submission request.",
            "links": entry.get("urls", []),
            "commit_hashes": [commit] if commit else [],
            "backfilled": True,
            "backfill_notes": ["The retained state stored one exact attempt timestamp rather than distinct start/end timestamps."],
            "source": {"system": "indexnow_state_history", "references": ["state/indexnow_state.json"]},
        })
    return output


def cli_test_events() -> list[dict[str, Any]]:
    output = []
    for commit, receipt in receipt_history("state/cli_ci.json"):
        timestamp = str(receipt["verified_at_utc"])
        run_url = str(receipt.get("workflow_run", ""))
        metadata = github_run_metadata(run_url, "pri8771/autonomous_apps")
        run_id = run_id_from_url(run_url) or f"backfill-{timestamp}"
        passed = receipt.get("status") == "passed"
        output.append({
            "event_id": stable_event_id("cli_tests", run_id),
            "run_id": run_id,
            "workflow": "cli_tests",
            "status": "success" if passed else "failed",
            "started_at_utc": metadata.get("run_started_at") or metadata.get("created_at") or timestamp,
            "ended_at_utc": metadata.get("updated_at") or timestamp,
            "trigger": metadata.get("event") or "not_recorded",
            "task_selected": {"id": "test-cli", "title": "Run deterministic CommerceLint CLI and Action tests", "type": "verification"},
            "decision_summary": "The retained CI receipt proves a product verification run; the exact historical trigger is used when workflow metadata is available.",
            "evidence_consulted": receipt.get("assertions", []),
            "action_taken": {"summary": "Ran the deterministic CLI, fixture, composite-action, and stable-reference checks.", "details": []},
            "verification": {"status": "passed" if passed else "failed", "summary": f"CI result: {receipt.get('test_result')}", "checks": []},
            "metrics_before": {},
            "metrics_after": {"assertion_count": len(receipt.get("assertions", []))},
            "blockers": [] if passed else ["CLI verification failed."],
            "failures_retries": [],
            "lessons": [],
            "next_action": "Retain the tested stable Action reference and rerun after relevant code changes.",
            "links": [run_url],
            "commit_hashes": [commit, str(receipt.get("tested_commit", "")), str(receipt.get("stable_action_commit", ""))],
            "backfilled": True,
            "backfill_notes": ([] if metadata else ["Workflow metadata was unavailable; the receipt timestamp is used for both start and end."]),
            "source": {"system": "cli_ci_git_history", "references": ["state/cli_ci.json"]},
        })
    return output


def watchdog_events() -> list[dict[str, Any]]:
    try:
        runs = command_json([
            "gh", "run", "list", "--workflow", "watchdog.yml", "--limit", "100", "--json",
            "databaseId,event,headSha,conclusion,createdAt,startedAt,updatedAt,url",
        ])
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []
    output = []
    for run in runs:
        run_id = str(run["databaseId"])
        conclusion = str(run.get("conclusion") or "unknown")
        passed = conclusion == "success"
        output.append({
            "event_id": stable_event_id("watchdog", run_id),
            "run_id": run_id,
            "workflow": "watchdog",
            "status": "success" if passed else conclusion,
            "started_at_utc": run.get("startedAt") or run.get("createdAt"),
            "ended_at_utc": run.get("updatedAt") or run.get("startedAt") or run.get("createdAt"),
            "trigger": run.get("event") or "not_recorded",
            "task_selected": {"id": "verify-heartbeat", "title": "Evaluate the operator heartbeat", "type": "monitoring"},
            "decision_summary": "The historical workflow metadata proves the watchdog ran, but it does not retain the heartbeat-age decision or whether recovery was dispatched.",
            "evidence_consulted": ["GitHub Actions watchdog run metadata", "state/state.json at the historical revision"],
            "action_taken": {"summary": f"The watchdog workflow completed with conclusion '{conclusion}'.", "details": []},
            "verification": {"status": "passed" if passed else "failed", "summary": f"GitHub Actions conclusion: {conclusion}", "checks": []},
            "metrics_before": {},
            "metrics_after": {},
            "blockers": [] if passed else [f"Historical watchdog conclusion: {conclusion}"],
            "failures_retries": [] if passed else [f"Historical watchdog conclusion: {conclusion}"],
            "lessons": [],
            "next_action": UNKNOWN,
            "links": [str(run.get("url", ""))],
            "commit_hashes": [str(run.get("headSha", ""))],
            "backfilled": True,
            "backfill_notes": ["Heartbeat age, stale/fresh decision, incident action, and recovery dispatch were not present in retained run metadata."],
            "source": {"system": "github_actions_metadata", "references": [str(run.get("url", ""))]},
        })
    return output


def deployment_events() -> list[dict[str, Any]]:
    endpoint = "repos/pri8771/priyanshchordia.com/commits?path=deployments/commercelint-production.json&per_page=100"
    try:
        commits = command_json(["gh", "api", endpoint])
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []
    output = []
    for item in reversed(commits):
        sha = str(item.get("sha", ""))
        try:
            encoded = command_json([
                "gh", "api",
                f"repos/pri8771/priyanshchordia.com/contents/deployments/commercelint-production.json?ref={sha}",
            ])
            receipt = json.loads(base64.b64decode(encoded["content"]).decode("utf-8"))
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError):
            continue
        event = receipt_event(receipt, backfilled=True)
        event.setdefault("commit_hashes", []).append(sha)
        event.setdefault("backfill_notes", []).append("This event was reconstructed from the versioned production deployment receipt.")
        output.append(event)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill the CommerceLint durable run diary from retained evidence.")
    parser.add_argument("--local-only", action="store_true", help="Skip GitHub workflow and external deployment metadata.")
    args = parser.parse_args()
    events = operator_events() + growth_events() + smoke_events() + indexnow_events() + cli_test_events()
    if not args.local_only:
        events += watchdog_events() + deployment_events()
    total, appended = record_events(events)
    print(json.dumps({"evidence_supported_events": total, "newly_appended": appended}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
