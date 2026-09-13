#!/usr/bin/env python3
"""Tests for plan contract, private intake and paid reports."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "operator"
sys.path.insert(0, str(OPERATOR))
sys.path.insert(0, str(ROOT / "cli"))

from plans import assert_plan_price, get_plan, load_plans_config  # noqa: E402
from private_intake import corrected_url_followup, record_validated_intake, validate_intake_request  # noqa: E402
from paid_report import page_reports_from_html, render_paid_markdown  # noqa: E402
from public_url import validate_url_batch  # noqa: E402


class PlanContractTests(unittest.TestCase):
    def test_three_prices_and_limits(self):
        config = load_plans_config()
        self.assertEqual(get_plan("sample", config)["price_usd"], 1.99)
        self.assertEqual(get_plan("lite", config)["max_public_product_urls"], 5)
        self.assertEqual(get_plan("comprehensive", config)["max_public_product_urls"], 15)
        self.assertEqual(assert_plan_price("sample", "1.99", config), assert_plan_price("sample", 1.99, config))

    def test_browser_price_override_rejected(self):
        with self.assertRaises(ValueError):
            assert_plan_price("lite", "0.01")


class IntakeTests(unittest.TestCase):
    def test_rejects_over_limit_before_charge(self):
        result = validate_intake_request(
            plan_id="sample",
            urls=["https://example.com/a", "https://example.com/b"],
            contact_email="buyer@example.com",
            claimed_price=1.99,
            resolve_dns=False,
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["charge_allowed"])
        self.assertEqual(result["status"], "rejected_urls")

    def test_rejects_private_host_before_charge(self):
        result = validate_intake_request(
            plan_id="sample",
            urls=["http://localhost/product"],
            contact_email="buyer@example.com",
            resolve_dns=False,
        )
        self.assertFalse(result["charge_allowed"])
        self.assertIn("Private or local", result["error"])

    def test_accepts_valid_sample_and_records_public_projection(self):
        result = validate_intake_request(
            plan_id="sample",
            urls=["https://example.com/product"],
            contact_email="buyer@example.com",
            claimed_price=1.99,
            resolve_dns=False,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["charge_allowed"])
        self.assertEqual(result["crm_project_id"], "commercelint")
        self.assertIn("primandir_hubspot_246481057", result["forbidden_crm"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "public.json"
            record = record_validated_intake(result, public_path=path)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(stored["inquiries"]), 1)
            self.assertNotIn("buyer@example.com", path.read_text(encoding="utf-8"))
            self.assertEqual(record["plan_id"], "sample")

    def test_corrected_url_followup(self):
        previous = {
            "status": "rejected_urls",
            "plan_id": "lite",
            "inquiry_id": "inq_test",
            "contact_email_fingerprint": "abc",
        }
        bad = corrected_url_followup(previous, new_urls=["not-a-url"], resolve_dns=False)
        self.assertFalse(bad["charge_allowed"])
        good = corrected_url_followup(
            previous,
            new_urls=["https://example.com/1", "https://example.com/2"],
            resolve_dns=False,
        )
        self.assertTrue(good["ok"])
        self.assertTrue(good["charge_allowed"])


class PaidReportTests(unittest.TestCase):
    def test_sample_report_from_fixture(self):
        html = (ROOT / "tests" / "fixtures" / "strong.html").read_text(encoding="utf-8")
        report = page_reports_from_html(
            "sample",
            [{"url": "https://example.com/product", "html": html}],
            order_id="ord_test",
            resolve_dns=False,
        )
        self.assertEqual(report["plan"]["id"], "sample")
        self.assertEqual(len(report["pages"]), 1)
        self.assertIsNone(report["comparison"])
        md = render_paid_markdown(report)
        self.assertIn("CommerceLint Sample report", md)
        self.assertIn("ord_test", md)

    def test_lite_rejects_too_many_pages(self):
        html = (ROOT / "tests" / "fixtures" / "strong.html").read_text(encoding="utf-8")
        pages = [{"url": f"https://example.com/p{i}", "html": html} for i in range(6)]
        with self.assertRaises(ValueError):
            page_reports_from_html("lite", pages, resolve_dns=False)

    def test_comprehensive_groups_repeated_issues(self):
        html = (ROOT / "tests" / "fixtures" / "missing-offer.html").read_text(encoding="utf-8")
        pages = [
            {"url": "https://example.com/a", "html": html},
            {"url": "https://example.com/b", "html": html},
        ]
        report = page_reports_from_html("comprehensive", pages, resolve_dns=False)
        self.assertIsNotNone(report["repeated_issues"])
        self.assertIsNotNone(report["retest_checklist"])
        self.assertIsNotNone(report["comparison"])


class UrlBatchTests(unittest.TestCase):
    def test_duplicate_rejection(self):
        batch = validate_url_batch(
            ["https://example.com/a", "https://example.com/a"],
            max_urls=5,
            resolve_dns=False,
        )
        self.assertFalse(batch["ok"])
        self.assertFalse(batch["charge_allowed"])


if __name__ == "__main__":
    unittest.main()
