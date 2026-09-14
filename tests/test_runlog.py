import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "operator"))

from runlog import record_event, record_events  # noqa: E402


def sample_event(event_id: str = "test-run-1") -> dict:
    return {
        "event_id": event_id,
        "run_id": event_id,
        "workflow": "test_workflow",
        "status": "success",
        "started_at_utc": "2026-08-25T04:05:06Z",
        "ended_at_utc": "2026-08-25T04:06:07Z",
        "trigger": "unit_test",
        "task_selected": {"id": "test", "title": "Verify logging", "type": "test"},
        "decision_summary": "Selected the bounded logger verification because the logging contract changed.",
        "evidence_consulted": ["tests/test_runlog.py"],
        "action_taken": {"summary": "Recorded a test event for customer@example.com.", "details": []},
        "verification": {"status": "passed", "summary": "All assertions passed.", "checks": []},
        "metrics_before": {"runs": 0, "api_token": "github_pat_abcdefghijklmnopqrstuvwxyz123456"},
        "metrics_after": {"runs": 1},
        "blockers": [],
        "failures_retries": [],
        "lessons": ["The logger is deterministic."],
        "next_action": "Continue normal operation.",
        "links": ["https://example.com/result?token=super-secret-value"],
        "commit_hashes": ["0123456789abcdef0123456789abcdef01234567"],
        "source": {"system": "unit_test", "references": []},
    }


class RunLogTests(unittest.TestCase):
    def test_record_builds_dual_format_diary_and_redacts_private_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event, appended = record_event(sample_event(), root=root)

            self.assertTrue(appended)
            self.assertEqual(event["started_at_local"], "2026-08-25T00:05:06-04:00")
            self.assertEqual(event["ended_at_local"], "2026-08-25T00:06:07-04:00")
            self.assertEqual(event["timezone"], "America/New_York")
            self.assertTrue(event["redaction_applied"])
            self.assertEqual(event["metrics_before"]["api_token"], "[REDACTED]")
            self.assertNotIn("customer@example.com", event["action_taken"]["summary"])
            self.assertIn("token=%5BREDACTED%5D", event["links"][0])

            events_path = root / "state/audit/events/2026-08-25.jsonl"
            daily_json = root / "state/audit/daily/2026-08-25.json"
            daily_markdown = root / "state/audit/daily/2026-08-25.md"
            index_json = root / "state/audit/index.json"
            index_markdown = root / "state/audit/INDEX.md"
            for path in (events_path, daily_json, daily_markdown, index_json, index_markdown):
                self.assertTrue(path.exists(), path)

            daily = json.loads(daily_json.read_text(encoding="utf-8"))
            self.assertEqual(daily["event_count"], 1)
            self.assertEqual(daily["events"][0]["event_id"], "test-run-1")
            markdown = daily_markdown.read_text(encoding="utf-8")
            self.assertIn("Decision summary", markdown)
            self.assertIn("Metrics", markdown)
            self.assertNotIn("customer@example.com", markdown)
            self.assertNotIn("super-secret-value", markdown)

            _, appended_again = record_event(sample_event(), root=root)
            self.assertFalse(appended_again)
            self.assertEqual(len(events_path.read_text(encoding="utf-8").splitlines()), 1)

    def test_batch_record_is_idempotent_and_preserves_required_schema_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            second = sample_event("test-run-2")
            second["started_at_utc"] = "2026-08-26T03:59:59Z"
            second["ended_at_utc"] = "2026-08-26T04:00:01Z"

            total, appended = record_events([sample_event(), second], root=root)
            self.assertEqual((total, appended), (2, 2))
            total, appended = record_events([sample_event(), second], root=root)
            self.assertEqual((total, appended), (2, 0))

            index = json.loads((root / "state/audit/index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["event_count"], 2)
            self.assertEqual(index["day_count"], 1)

            required = set(json.loads((ROOT / "state/audit/schema.json").read_text(encoding="utf-8"))["required"])
            event = json.loads((root / "state/audit/events/2026-08-25.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertFalse(required - set(event), required - set(event))


if __name__ == "__main__":
    unittest.main()
