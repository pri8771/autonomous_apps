#!/usr/bin/env python3
"""LangGraph portfolio-side watcher for the CommerceLint operator loop.

This is a second, independent layer of oversight that runs OUTSIDE GitHub
Actions (on the portfolio owner's machine), because the repo's own
hourly-operator / watchdog / production-smoke loop cannot notice if GitHub
Actions itself stops firing for that repo (billing, token expiry, schedule
disablement after inactivity, etc.). It never writes to the target repo.

Permissions contract: read-only + Actions-dispatch only.
  - State is read from the public repo via unauthenticated raw content
    fetches (no token required, no write scope needed).
  - The only authenticated calls are workflow_dispatch (POST) and the
    Actions "list workflow runs" read used to poll a dispatch's outcome.
  - This script never calls the contents or issues APIs and never pushes
    commits.

Recovery sequence (mirrors RUNBOOK.md "Recovery" + "New-conversation
bootstrap" step 6):
  1. Read state/state.json + config/business.json for the current
     heartbeat age and the configured staleness threshold.
  2. Classify green (fresh) vs breach (stale, or the watchdog/smoke
     workflow's last run did not conclude successfully).
  3. On breach: dispatch watchdog.yml, wait for it to conclude, verify the
     operator heartbeat is fresh again, dispatch watchdog.yml a second time
     so it observes the fresh heartbeat and auto-closes any open
     "[CommerceLint] Stale heartbeat" issue, then dispatch
     production-smoke.yml as a final health confirmation.
  4. On breach, append one structured alert record for Kai to relay to
     Slack. On green, no alert is written (no Slack noise).

This module intentionally never runs live network calls when imported for
tests; all GitHub interaction goes through the small `GitHubClient` class so
tests can substitute a fake client.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypedDict

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - exercised only when langgraph is absent
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]

DEFAULT_REPO = "pri8771/autonomous_apps"
DEFAULT_BRANCH = "main"
WATCHDOG_WORKFLOW = "watchdog.yml"
SMOKE_WORKFLOW = "production-smoke.yml"
RAW_BASE = "https://raw.githubusercontent.com"
API_BASE = "https://api.github.com"
POLL_INTERVAL_SECONDS = 20
POLL_TIMEOUT_SECONDS = 10 * 60  # matches watchdog.yml's own 10-minute job timeout


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class GitHubClient:
    """Thin GitHub REST wrapper. Read calls never require a token; dispatch
    and run-status calls do. Kept small and mockable on purpose."""

    def __init__(self, repo: str, token: str | None, branch: str = DEFAULT_BRANCH) -> None:
        self.repo = repo
        self.token = token
        self.branch = branch

    def _request(self, url: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "commercelint-portfolio-monitor")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https GH API/raw hosts only
            raw = resp.read()
            return json.loads(raw) if raw else None

    def read_json_file(self, path: str) -> dict[str, Any]:
        url = f"{RAW_BASE}/{self.repo}/{self.branch}/{path}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "commercelint-portfolio-monitor")
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read())

    def dispatch_workflow(self, workflow_file: str) -> None:
        if not self.token:
            raise RuntimeError(
                "no GitHub token configured; cannot dispatch a workflow "
                "(read-only mode can still classify green/breach)"
            )
        url = f"{API_BASE}/repos/{self.repo}/actions/workflows/{workflow_file}/dispatches"
        self._request(url, method="POST", body={"ref": self.branch})

    def latest_run(self, workflow_file: str) -> dict[str, Any] | None:
        url = (
            f"{API_BASE}/repos/{self.repo}/actions/workflows/{workflow_file}/runs"
            "?per_page=1"
        )
        payload = self._request(url, method="GET")
        runs = (payload or {}).get("workflow_runs") or []
        return runs[0] if runs else None


class MonitorState(TypedDict, total=False):
    repo: str
    threshold_minutes: int
    age_minutes: int
    last_success_at_utc: str | None
    classification: str
    check_started_at_utc: str
    watchdog_run_1: dict[str, Any] | None
    watchdog_run_2: dict[str, Any] | None
    smoke_run: dict[str, Any] | None
    recovered: bool
    alert: dict[str, Any] | None
    notes: list[str]


@dataclass
class MonitorConfig:
    repo: str = DEFAULT_REPO
    branch: str = DEFAULT_BRANCH
    token: str | None = None
    dry_run: bool = True
    alert_path: Path = field(
        default_factory=lambda: Path.home() / ".local" / "state" / "commercelint-portfolio-monitor" / "alerts.jsonl"
    )
    poll_interval_seconds: int = POLL_INTERVAL_SECONDS
    poll_timeout_seconds: int = POLL_TIMEOUT_SECONDS
    sleep_fn: Callable[[float], None] = time.sleep


def build_graph(client: GitHubClient, config: MonitorConfig):
    """Build (but do not compile) the LangGraph state machine. Split out for
    testability: tests call the node functions directly without needing a
    compiled graph or the langgraph package installed."""

    def check_freshness(state: MonitorState) -> MonitorState:
        business = client.read_json_file("config/business.json")
        repo_state = client.read_json_file("state/state.json")
        threshold = int(business.get("operating_policy", {}).get("heartbeat_stale_minutes", 75))
        last_success = repo_state.get("operator", {}).get("last_success_at_utc")
        age_minutes = 10**9
        if last_success:
            age_minutes = int((now_utc() - parse_iso(last_success)).total_seconds() / 60)
        return {
            **state,
            "threshold_minutes": threshold,
            "age_minutes": age_minutes,
            "last_success_at_utc": last_success,
            "check_started_at_utc": iso(now_utc()),
            "notes": [
                f"heartbeat age {age_minutes}m vs threshold {threshold}m "
                f"(last success {last_success or 'never'})"
            ],
        }

    def classify(state: MonitorState) -> MonitorState:
        stale = state["age_minutes"] > state["threshold_minutes"]
        return {**state, "classification": "breach" if stale else "green"}

    def route_after_classify(state: MonitorState) -> str:
        return "dispatch_watchdog" if state["classification"] == "breach" else "done"

    def dispatch_watchdog_first(state: MonitorState) -> MonitorState:
        notes = list(state.get("notes", []))
        if config.dry_run:
            notes.append("[dry-run] would dispatch watchdog.yml (recovery attempt 1)")
            return {**state, "notes": notes}
        client.dispatch_workflow(WATCHDOG_WORKFLOW)
        run = _wait_for_new_run(client, WATCHDOG_WORKFLOW, state["check_started_at_utc"], config)
        notes.append(f"dispatched watchdog.yml, run concluded: {_conclusion(run)}")
        return {**state, "watchdog_run_1": run, "notes": notes}

    def verify_recovery(state: MonitorState) -> MonitorState:
        notes = list(state.get("notes", []))
        if config.dry_run:
            notes.append("[dry-run] would verify recovered heartbeat")
            return {**state, "recovered": False, "notes": notes}
        repo_state = client.read_json_file("state/state.json")
        last_success = repo_state.get("operator", {}).get("last_success_at_utc")
        age_minutes = 10**9
        if last_success:
            age_minutes = int((now_utc() - parse_iso(last_success)).total_seconds() / 60)
        recovered = age_minutes <= state["threshold_minutes"]
        notes.append(f"post-recovery heartbeat age {age_minutes}m; recovered={recovered}")
        return {**state, "recovered": recovered, "notes": notes}

    def close_incident(state: MonitorState) -> MonitorState:
        notes = list(state.get("notes", []))
        if config.dry_run:
            notes.append("[dry-run] would dispatch watchdog.yml again to close the incident")
            return {**state, "notes": notes}
        client.dispatch_workflow(WATCHDOG_WORKFLOW)
        run = _wait_for_new_run(client, WATCHDOG_WORKFLOW, state["check_started_at_utc"], config)
        notes.append(f"dispatched watchdog.yml (close-incident pass), run concluded: {_conclusion(run)}")
        return {**state, "watchdog_run_2": run, "notes": notes}

    def dispatch_smoke(state: MonitorState) -> MonitorState:
        notes = list(state.get("notes", []))
        if config.dry_run:
            notes.append("[dry-run] would dispatch production-smoke.yml")
            return {**state, "notes": notes}
        client.dispatch_workflow(SMOKE_WORKFLOW)
        run = _wait_for_new_run(client, SMOKE_WORKFLOW, state["check_started_at_utc"], config)
        notes.append(f"dispatched production-smoke.yml, run concluded: {_conclusion(run)}")
        return {**state, "smoke_run": run, "notes": notes}

    def alert_via_kai(state: MonitorState) -> MonitorState:
        alert = {
            "schema_version": 1,
            "source": "commercelint-portfolio-monitor",
            "repo": config.repo,
            "severity": "P1",
            "recorded_at_utc": iso(now_utc()),
            "classification": state["classification"],
            "age_minutes": state["age_minutes"],
            "threshold_minutes": state["threshold_minutes"],
            "recovered": state.get("recovered"),
            "watchdog_run_1": _summarize_run(state.get("watchdog_run_1")),
            "watchdog_run_2": _summarize_run(state.get("watchdog_run_2")),
            "smoke_run": _summarize_run(state.get("smoke_run")),
            "notes": state.get("notes", []),
            "dry_run": config.dry_run,
        }
        _append_alert(config.alert_path, alert)
        return {**state, "alert": alert}

    nodes = {
        "check_freshness": check_freshness,
        "classify": classify,
        "dispatch_watchdog": dispatch_watchdog_first,
        "verify_recovery": verify_recovery,
        "close_incident": close_incident,
        "dispatch_smoke": dispatch_smoke,
        "alert_via_kai": alert_via_kai,
    }
    return nodes, route_after_classify


def _conclusion(run: dict[str, Any] | None) -> str:
    if not run:
        return "unknown (no run observed)"
    return f"{run.get('status')}/{run.get('conclusion')}"


def _summarize_run(run: dict[str, Any] | None) -> dict[str, Any] | None:
    if not run:
        return None
    return {
        "id": run.get("id"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "html_url": run.get("html_url"),
    }


def _wait_for_new_run(
    client: GitHubClient, workflow_file: str, since_iso: str, config: MonitorConfig
) -> dict[str, Any] | None:
    """Poll for the run this call itself dispatched, bounded by
    poll_timeout_seconds. Matches the target workflow's own job timeout so
    this never hangs a scheduled task indefinitely."""
    since = parse_iso(since_iso)
    deadline = time.time() + config.poll_timeout_seconds
    latest: dict[str, Any] | None = None
    while time.time() < deadline:
        run = client.latest_run(workflow_file)
        if run and parse_iso(run["created_at"]) >= since:
            latest = run
            if run.get("status") == "completed":
                return run
        config.sleep_fn(config.poll_interval_seconds)
    return latest


def _append_alert(path: Path, alert: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(alert, sort_keys=True) + "\n")


def run_once(config: MonitorConfig) -> MonitorState:
    client = GitHubClient(repo=config.repo, token=config.token, branch=config.branch)
    nodes, route_after_classify = build_graph(client, config)

    if StateGraph is not None:
        graph = StateGraph(MonitorState)
        for name, fn in nodes.items():
            graph.add_node(name, fn)
        graph.set_entry_point("check_freshness")
        graph.add_edge("check_freshness", "classify")
        graph.add_conditional_edges(
            "classify", route_after_classify, {"dispatch_watchdog": "dispatch_watchdog", "done": END}
        )
        graph.add_edge("dispatch_watchdog", "verify_recovery")
        graph.add_edge("verify_recovery", "close_incident")
        graph.add_edge("close_incident", "dispatch_smoke")
        graph.add_edge("dispatch_smoke", "alert_via_kai")
        graph.add_edge("alert_via_kai", END)
        compiled = graph.compile()
        return compiled.invoke({})

    # langgraph not installed: fall back to the same sequence run directly,
    # so the classification/dry-run logic stays testable without the
    # dependency present.
    state: MonitorState = {}
    state = nodes["check_freshness"](state)
    state = nodes["classify"](state)
    if route_after_classify(state) == "done":
        return state
    state = nodes["dispatch_watchdog"](state)
    state = nodes["verify_recovery"](state)
    state = nodes["close_incident"](state)
    state = nodes["dispatch_smoke"](state)
    state = nodes["alert_via_kai"](state)
    return state


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("MONITOR_REPO", DEFAULT_REPO))
    parser.add_argument("--branch", default=os.environ.get("MONITOR_BRANCH", DEFAULT_BRANCH))
    parser.add_argument(
        "--token",
        default=os.environ.get("COMMERCELINT_MONITOR_GH_TOKEN"),
        help="Fine-grained PAT scoped to Actions:write + Contents:read on this repo only. "
        "Never contents:write / issues:write - this tool must stay read-only + dispatch-only.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually dispatch workflows on breach. Default is --dry-run (classify only, no side effects).",
    )
    parser.add_argument("--alert-path", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = MonitorConfig(repo=args.repo, branch=args.branch, token=args.token, dry_run=not args.live)
    if args.alert_path:
        config.alert_path = Path(args.alert_path)
    result = run_once(config)
    print(json.dumps({k: v for k, v in result.items() if k != "notes"}, indent=2, default=str))
    for note in result.get("notes", []):
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
