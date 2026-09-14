#!/usr/bin/env python3
"""S01-06 site readiness: routes, pricing truth, paid CTA gated, experiment setup."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class SiteReadinessTests(unittest.TestCase):
    def test_required_public_routes_exist(self):
        required = [
            "index.html",
            "pricing.html",
            "scanner.html",
            "privacy.html",
            "founding-audit.html",
            "sample-audit.html",
            "guides/index.html",
            "guides/strong-product-page-field-coverage-example.html",
            "guides/missing-offer-lite-comparison-example.html",
            "guides/unsupported-page-kinds-example.html",
            "assets/service-readiness.js",
            "assets/inquiry.js",
            "assets/analytics.js",
            "assets/plans.js",
            "service.json",
            "sitemap.xml",
        ]
        for rel in required:
            self.assertTrue((DOCS / rel).exists(), rel)

    def test_paid_checkout_unavailable_and_prices_match(self):
        service = json.loads((DOCS / "service.json").read_text(encoding="utf-8"))
        paid = service["paid_service"]
        self.assertFalse(paid["paid_checkout_available"])
        self.assertFalse(paid["stripe_sandbox_observed"])
        self.assertIn("Unavailable", paid["checkout_status"])
        prices = {p["id"]: p["price"] for p in paid["plans"]}
        self.assertEqual(prices, {"sample": 1.99, "lite": 9.99, "comprehensive": 19.99})
        pricing = (DOCS / "pricing.html").read_text(encoding="utf-8")
        self.assertIn("paid checkout is unavailable", pricing.lower())
        self.assertIn("data-cl-paid-checkout", pricing)
        self.assertIn("service-readiness.js", pricing)
        self.assertNotIn("https://checkout.stripe.com", pricing)
        readiness = (DOCS / "assets" / "service-readiness.js").read_text(encoding="utf-8")
        self.assertIn("paid_checkout_available: false", readiness)

    def test_contact_and_inquiry_paths(self):
        founding = (DOCS / "founding-audit.html").read_text(encoding="utf-8")
        self.assertIn("inquiry.js", founding)
        self.assertIn("service-readiness.js", founding)
        self.assertIn("pchordia@unsubscriber.me", founding + (DOCS / "pricing.html").read_text())
        privacy = (DOCS / "privacy.html").read_text(encoding="utf-8")
        self.assertTrue(len(privacy) > 200)

    def test_sitemap_includes_worked_examples_and_pricing(self):
        sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
        for needle in (
            "pricing.html",
            "guides/strong-product-page-field-coverage-example.html",
            "guides/missing-offer-lite-comparison-example.html",
            "guides/unsupported-page-kinds-example.html",
            "privacy.html",
        ):
            self.assertIn(needle, sitemap)

    def test_owned_channel_experiment_setup(self):
        rows = list(csv.DictReader((ROOT / "EXPERIMENTS.csv").read_text(encoding="utf-8").splitlines()))
        match = [r for r in rows if r["id"] == "cl-guides-to-pricing-v1"]
        self.assertEqual(len(match), 1)
        row = match[0]
        self.assertEqual(row["status"], "setup_complete_observation_open")
        self.assertIn("inconclusive", row["result"])
        self.assertIn("paid checkout remains unavailable", row["change"].lower())


if __name__ == "__main__":
    unittest.main()
