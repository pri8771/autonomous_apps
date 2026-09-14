import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AnalyticsTests(unittest.TestCase):
    def test_runtime_and_config_use_the_verified_property(self):
        runtime = (ROOT / "docs" / "assets" / "analytics.js").read_text(encoding="utf-8")
        config = json.loads((ROOT / "config" / "business.json").read_text(encoding="utf-8"))
        measurement_id = config["site"]["analytics_measurement_id"]
        self.assertEqual(measurement_id, "G-MC3PB0Q7EX")
        self.assertIn(f'const MEASUREMENT_ID = "{measurement_id}"', runtime)
        self.assertIn('readConsent() !== "granted"', runtime)
        self.assertIn("send_page_view: false", runtime)
        self.assertIn("window.commerceLintTrack = track", runtime)

    def test_event_names_are_ga4_safe_and_sensitive_fields_are_not_allowed(self):
        runtime = (ROOT / "docs" / "assets" / "analytics.js").read_text(encoding="utf-8")
        self.assertRegex(runtime, re.compile(r"function safeEventName\(value\).*?\[\^a-z0-9_\]", re.S))
        allowlist = re.search(r"const stringFields = \[(.*?)\];", runtime, re.S)
        self.assertIsNotNone(allowlist)
        self.assertNotIn('"store_url"', allowlist.group(1))
        self.assertNotIn('"email"', allowlist.group(1))
        self.assertNotIn('"form_contents"', allowlist.group(1))


if __name__ == "__main__":
    unittest.main()
