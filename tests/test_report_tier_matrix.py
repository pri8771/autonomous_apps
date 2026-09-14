#!/usr/bin/env python3
"""Six-case sample/lite/comprehensive report-tier matrix for S01-05."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "operator"))
sys.path.insert(0, str(ROOT / "cli"))

from paid_report import classify_page_support, page_reports_from_html, render_paid_markdown  # noqa: E402
from plans import get_plan, load_plans_config  # noqa: E402
from private_intake import validate_intake_request  # noqa: E402
from commercelint import analyze_html  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"

CASES = [
    ("strong_product", "strong.html", "https://example.com/products/linen-shirt", True),
    ("missing_offer", "missing-offer.html", "https://example.com/products/incomplete", True),
    ("offer_no_currency", "offer-no-currency.html", "https://example.com/products/currency-gap-mug", True),
    ("malformed_jsonld", "malformed-jsonld.html", "https://example.com/products/broken-jsonld", False),
    ("non_product_blog", "non-product-blog.html", "https://example.com/blog/autumn-trends", False),
    ("login_wall", "login-wall.html", "https://example.com/account/login", False),
]


class ReportTierMatrixTests(unittest.TestCase):
    def test_six_cases_exist(self):
        self.assertEqual(len(CASES), 6)
        for _name, filename, _url, _supported in CASES:
            self.assertTrue((FIXTURES / filename).exists(), filename)

    def test_unsupported_not_scored_as_product(self):
        html = (FIXTURES / "non-product-blog.html").read_text(encoding="utf-8")
        analysis = analyze_html(html, source="blog")
        # Prior false narrative: product-field fails with a numeric score.
        self.assertGreater(analysis["score"], 0)
        support = classify_page_support(html, analysis)
        self.assertFalse(support["supported"])
        report = page_reports_from_html(
            "sample",
            [{"url": "https://example.com/blog/autumn-trends", "html": html}],
            resolve_dns=False,
        )
        page = report["pages"][0]
        self.assertIsNone(page["score"])
        self.assertEqual(page["checks"][0]["id"], "unsupported-page")
        self.assertIn("product page", page["checks"][0]["repair"].lower())
        self.assertTrue(page.get("underlying_checks"))

    def test_empty_html_fails_before_report(self):
        with self.assertRaises(ValueError) as ctx:
            page_reports_from_html(
                "sample",
                [{"url": "https://example.com/empty", "html": "   "}],
                resolve_dns=False,
            )
        self.assertIn("Unsupported empty", str(ctx.exception))

    def test_private_host_fails_before_charge(self):
        result = validate_intake_request(
            plan_id="sample",
            urls=["http://localhost/product"],
            contact_email="buyer@example.com",
            resolve_dns=False,
        )
        self.assertFalse(result["charge_allowed"])

    def test_tier_contract_and_matrix_behaviors(self):
        config = load_plans_config()
        self.assertEqual(get_plan("sample", config)["price_usd"], 1.99)
        self.assertEqual(get_plan("lite", config)["price_usd"], 9.99)
        self.assertEqual(get_plan("comprehensive", config)["price_usd"], 19.99)

        matrix = []
        for name, filename, url, expect_supported in CASES:
            html = (FIXTURES / filename).read_text(encoding="utf-8")
            sample = page_reports_from_html("sample", [{"url": url, "html": html}], resolve_dns=False)
            page = sample["pages"][0]
            supported = bool((page.get("page_support") or {}).get("supported"))
            self.assertEqual(supported, expect_supported, name)
            row = {
                "case": name,
                "url": url,
                "fixture": filename,
                "supported": supported,
                "sample_score": page.get("score"),
                "sample_primary_check": page["checks"][0]["id"],
                "sample_has_comparison": sample.get("comparison") is not None,
                "sample_has_repeated": sample.get("repeated_issues") is not None,
                "sample_has_retest": sample.get("retest_checklist") is not None,
            }
            if expect_supported and name != "strong_product":
                # Incomplete product pages keep product diagnostics.
                self.assertIsNotNone(page.get("score"))
            matrix.append(row)

        # Lite comparison requires 2+ scored pages
        strong = (FIXTURES / "strong.html").read_text(encoding="utf-8")
        missing = (FIXTURES / "missing-offer.html").read_text(encoding="utf-8")
        lite = page_reports_from_html(
            "lite",
            [
                {"url": "https://example.com/a", "html": strong},
                {"url": "https://example.com/b", "html": missing},
            ],
            resolve_dns=False,
        )
        self.assertIsNotNone(lite["comparison"])
        self.assertIsNone(lite["repeated_issues"])

        comprehensive = page_reports_from_html(
            "comprehensive",
            [
                {"url": "https://example.com/a", "html": missing},
                {"url": "https://example.com/b", "html": missing},
            ],
            resolve_dns=False,
        )
        self.assertIsNotNone(comprehensive["comparison"])
        self.assertIsNotNone(comprehensive["repeated_issues"])
        self.assertIsNotNone(comprehensive["retest_checklist"])

        # Pricing consistency: report plan prices match config
        for plan_id, price in (("sample", 1.99), ("lite", 9.99), ("comprehensive", 19.99)):
            report = page_reports_from_html(
                plan_id,
                [{"url": "https://example.com/products/linen-shirt", "html": strong}],
                resolve_dns=False,
            )
            self.assertEqual(report["plan"]["price_usd"], price)
            md = render_paid_markdown(report)
            self.assertIn(f"${price} USD", md)

        self.assertEqual(len(matrix), 6)
        # Attach for evidence consumers via attribute
        self.matrix = matrix  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
