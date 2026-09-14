import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "operator"))

import watchdog  # noqa: E402


class WatchdogTests(unittest.TestCase):
    def evaluate(self, last_success_at_utc):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "state.json"
            config_path = root / "business.json"
            state_path.write_text(
                json.dumps({"operator": {"last_success_at_utc": last_success_at_utc}}),
                encoding="utf-8",
            )
            config_path.write_text(
                json.dumps({"operating_policy": {"heartbeat_stale_minutes": 75}}),
                encoding="utf-8",
            )
            now = datetime(2026, 8, 26, 10, 17, tzinfo=timezone.utc)
            with (
                patch.object(watchdog, "STATE_PATH", state_path),
                patch.object(watchdog, "CONFIG_PATH", config_path),
                patch.object(watchdog, "now_utc", return_value=now),
                patch.dict(os.environ, {"GITHUB_EVENT_NAME": "schedule"}, clear=False),
            ):
                return watchdog.evaluate()

    def test_hour_boundary_does_not_create_false_stale_incident(self):
        result = self.evaluate("2026-08-26T09:56:00Z")

        self.assertEqual(result["age_minutes"], 21)
        self.assertTrue(result["missed_current_hour"])
        self.assertFalse(result["stale"])
        self.assertIn("within the age threshold", result["reason"])

    def test_heartbeat_older_than_threshold_is_stale(self):
        result = self.evaluate("2026-08-26T08:59:00Z")

        self.assertEqual(result["age_minutes"], 78)
        self.assertTrue(result["stale"])
        self.assertIn("exceeded the 75-minute", result["reason"])

    def test_missing_heartbeat_is_stale(self):
        result = self.evaluate(None)

        self.assertTrue(result["stale"])
        self.assertEqual(result["reason"], "no successful heartbeat exists")


if __name__ == "__main__":
    unittest.main()
