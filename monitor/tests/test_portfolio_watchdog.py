"""Deterministic tests for the portfolio-side CommerceLint watchdog monitor.

These run without network access and without requiring langgraph to be
installed (the module falls back to running its node functions directly in
that case), so they stay fast and dependency-light. Run with:

    python -m unittest discover -s monitor/tests -v
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import portfolio_watchdog as pw  # noqa: E402


class FakeGitHubClient:
    """Records every call instead of touching the network. Configurable
    fixtures let each test drive a specific scenario."""

    def __init__(self, files: dict[str, dict], runs: dict[str, list[dict]]):
        self.repo = "pri8771/autonomous_apps"
        self.token = "fake-token"
        self._files = files
        self._runs = {name: list(entries) for name, entries in runs.items()}
        self.dispatch_calls: list[str] = []
        self.latest_run_calls: list[str] = []

    def read_json_file(self, path: str):
        return self._files[path]

    def dispatch_workflow(self, workflow_file: str) -> None:
        self.dispatch_calls.append(workflow_file)

    def latest_run(self, workflow_file: str):
        self.latest_run_calls.append(workflow_file)
        queue = self._runs.get(workflow_file, [])
        return queue.pop(0) if queue else None


def _business(threshold: int = 75) -> dict:
    return {"operating_policy": {"heartbeat_stale_minutes": threshold}}


def _state(last_success_iso: str | None) -> dict:
    return {"operator": {"last_success_at_utc": last_success_iso}}


def _completed_run(run_id: int, conclusion: str, created_at_iso: str) -> dict:
    return {
        "id": run_id,
        "status": "completed",
        "conclusion": conclusion,
        "created_at": created_at_iso,
        "html_url": f"https://github.com/pri8771/autonomous_apps/actions/runs/{run_id}",
    }


class ClassifyTests(unittest.TestCase):
    def test_green_when_heartbeat_is_fresh(self):
        fresh = pw.iso(pw.now_utc())
        files = {"config/business.json": _business(75), "state/state.json": _state(fresh)}
        client = FakeGitHubClient(files, runs={})
        nodes, route = pw.build_graph(client, pw.MonitorConfig(dry_run=True))

        state = nodes["check_freshness"]({})
        state = nodes["classify"](state)

        self.assertEqual(state["classification"], "green")
        self.assertEqual(route(state), "done")
        self.assertLessEqual(state["age_minutes"], 1)

    def test_breach_when_heartbeat_is_older_than_threshold(self):
        # 200 minutes old, well past the 75-minute default threshold
        from datetime import timedelta

        old = pw.iso(pw.now_utc() - timedelta(minutes=200))
        files = {"config/business.json": _business(75), "state/state.json": _state(old)}
        client = FakeGitHubClient(files, runs={})
        nodes, route = pw.build_graph(client, pw.MonitorConfig(dry_run=True))

        state = nodes["check_freshness"]({})
        state = nodes["classify"](state)

        self.assertEqual(state["classification"], "breach")
        self.assertEqual(route(state), "dispatch_watchdog")
        self.assertGreaterEqual(state["age_minutes"], 199)

    def test_breach_when_no_heartbeat_recorded_yet(self):
        files = {"config/business.json": _business(75), "state/state.json": _state(None)}
        client = FakeGitHubClient(files, runs={})
        nodes, route = pw.build_graph(client, pw.MonitorConfig(dry_run=True))

        state = nodes["classify"](nodes["check_freshness"]({}))

        self.assertEqual(state["classification"], "breach")


class GreenPathTests(unittest.TestCase):
    def test_green_path_produces_no_alert_and_no_dispatch(self):
        with TemporaryDirectory() as tmp:
            alert_path = Path(tmp) / "alerts.jsonl"
            fresh = pw.iso(pw.now_utc())
            files = {"config/business.json": _business(75), "state/state.json": _state(fresh)}
            client = FakeGitHubClient(files, runs={})
            config = pw.MonitorConfig(dry_run=False, alert_path=alert_path, sleep_fn=lambda _s: None)

            nodes, route = pw.build_graph(client, config)
            state = nodes["classify"](nodes["check_freshness"]({}))
            self.assertEqual(route(state), "done")

            self.assertEqual(client.dispatch_calls, [])
            self.assertFalse(alert_path.exists())


class BreachPathTests(unittest.TestCase):
    def test_breach_path_dispatches_recovery_sequence_and_writes_one_alert(self):
        with TemporaryDirectory() as tmp:
            alert_path = Path(tmp) / "alerts.jsonl"
            from datetime import timedelta

            old = pw.iso(pw.now_utc() - timedelta(minutes=200))
            fresh = pw.iso(pw.now_utc())
            files_sequence = [
                {"config/business.json": _business(75), "state/state.json": _state(old)},
                # verify_recovery re-reads state/state.json after the first dispatch
                {"config/business.json": _business(75), "state/state.json": _state(fresh)},
            ]

            class SequencedClient(FakeGitHubClient):
                def __init__(self):
                    super().__init__(files_sequence[0], runs={
                        "watchdog.yml": [
                            _completed_run(1, "success", pw.iso(pw.now_utc())),
                            _completed_run(2, "success", pw.iso(pw.now_utc())),
                        ],
                        "production-smoke.yml": [
                            _completed_run(3, "success", pw.iso(pw.now_utc())),
                        ],
                    })
                    self._reads = 0

                def read_json_file(self, path):
                    if path == "state/state.json":
                        # first read via check_freshness, second via verify_recovery
                        payload = files_sequence[min(self._reads, len(files_sequence) - 1)][path]
                        self._reads += 1
                        return payload
                    return files_sequence[0][path]

            client = SequencedClient()
            config = pw.MonitorConfig(
                dry_run=False,
                alert_path=alert_path,
                sleep_fn=lambda _s: None,
                poll_timeout_seconds=5,
                poll_interval_seconds=0,
            )
            nodes, route = pw.build_graph(client, config)

            state = nodes["check_freshness"]({})
            state = nodes["classify"](state)
            self.assertEqual(route(state), "dispatch_watchdog")

            state = nodes["dispatch_watchdog"](state)
            state = nodes["verify_recovery"](state)
            state = nodes["close_incident"](state)
            state = nodes["dispatch_smoke"](state)
            state = nodes["alert_via_kai"](state)

            self.assertEqual(client.dispatch_calls, ["watchdog.yml", "watchdog.yml", "production-smoke.yml"])
            self.assertTrue(state["recovered"])
            self.assertTrue(alert_path.exists())

            lines = alert_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            alert = json.loads(lines[0])
            self.assertEqual(alert["classification"], "breach")
            self.assertTrue(alert["recovered"])
            self.assertEqual(alert["watchdog_run_1"]["conclusion"], "success")
            self.assertEqual(alert["smoke_run"]["conclusion"], "success")


class PermissionSafetyTests(unittest.TestCase):
    def test_dispatch_without_token_refuses_instead_of_silently_no_op(self):
        client = pw.GitHubClient(repo="pri8771/autonomous_apps", token=None)
        with self.assertRaises(RuntimeError):
            client.dispatch_workflow("watchdog.yml")

    def test_read_json_file_uses_unauthenticated_raw_url_helper(self):
        # Read access must not require a token: confirm the client builds
        # the public raw.githubusercontent.com URL regardless of token state.
        client = pw.GitHubClient(repo="pri8771/autonomous_apps", token=None)
        self.assertIn("raw.githubusercontent.com", pw.RAW_BASE)
        self.assertIsNone(client.token)


if __name__ == "__main__":
    unittest.main()
