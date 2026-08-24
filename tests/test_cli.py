from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "cli" / "commercelint.py"
FIXTURES = ROOT / "tests" / "fixtures"

spec = importlib.util.spec_from_file_location("commercelint_cli", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class CommerceLintTests(unittest.TestCase):
    def test_strong_fixture_scores_100(self) -> None:
        report = module.analyze_html(
            (FIXTURES / "strong.html").read_text(encoding="utf-8"),
            source="strong.html",
        )
        self.assertEqual(report["score"], 100)
        self.assertEqual(report["counts"]["fail"], 0)
        self.assertEqual(report["counts"]["warning"], 0)

    def test_missing_offer_is_a_failure(self) -> None:
        report = module.analyze_html(
            (FIXTURES / "missing-offer.html").read_text(encoding="utf-8"),
            source="missing.html",
        )
        failed = {check["id"] for check in report["checks"] if check["status"] == "fail"}
        self.assertTrue({"offer-object", "price", "currency", "availability"}.issubset(failed))
        self.assertLess(report["score"], 70)

    def test_malformed_jsonld_is_reported(self) -> None:
        markup = '<html><head><script type="application/ld+json">{bad}</script></head><body></body></html>'
        report = module.analyze_html(markup)
        self.assertEqual(report["counts"]["fail"], 7)
        self.assertTrue(report["structured_data"]["parse_errors"])

    def test_cli_failure_policy(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(FIXTURES / "missing-offer.html"),
                "--format",
                "json",
                "--fail-on",
                "fail",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 1)
        report = json.loads(completed.stdout)
        self.assertGreater(report["counts"]["fail"], 0)

    def test_markdown_renderer_has_limitations(self) -> None:
        report = module.analyze_html((FIXTURES / "strong.html").read_text(encoding="utf-8"))
        rendered = module.render_markdown(report)
        self.assertIn("# CommerceLint field coverage report", rendered)
        self.assertIn("## Limitations", rendered)


if __name__ == "__main__":
    unittest.main()
