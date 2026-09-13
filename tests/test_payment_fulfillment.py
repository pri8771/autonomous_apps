#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "operator"))

from payment_fulfillment import (  # noqa: E402
    checkout_to_fulfilled_demo,
    create_pending_order,
    open_support_case,
    record_payment_webhook,
    verify_webhook_signature,
)


class PaymentFulfillmentTests(unittest.TestCase):
    def test_rejects_unsupported_urls_before_order(self):
        result = create_pending_order(
            plan_id="sample",
            urls=["http://localhost/x"],
            contact_email="buyer@example.com",
            resolve_dns=False,
            orders_path=Path(tempfile.mkdtemp()) / "orders.json",
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["charge_allowed"])

    def test_webhook_signature_and_replay(self):
        secret = "test_secret"
        payload = b'{"id":"evt_1"}'
        good = "sha256=" + __import__("hmac").new(secret.encode(), payload, __import__("hashlib").sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(payload, secret, good))
        self.assertFalse(verify_webhook_signature(payload, "", good))
        self.assertFalse(verify_webhook_signature(payload, secret, "sha256=deadbeef"))

    def test_checkout_through_fulfilled_report_demo(self):
        html = (ROOT / "tests" / "fixtures" / "strong.html").read_text(encoding="utf-8")
        result = checkout_to_fulfilled_demo(
            plan_id="sample",
            urls=["https://example.com/product"],
            contact_email="buyer@example.com",
            pages=[{"url": "https://example.com/product", "html": html}],
            provider_event_id="evt_demo_1",
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["webhook_duplicate_replay"])
        self.assertEqual(result["job"]["status"], "fulfilled")
        self.assertEqual(result["order"]["payment_state"], "succeeded")
        self.assertFalse(result["checkout_live"])
        self.assertTrue(Path(result["job"]["report_markdown_path"]).exists())

    def test_support_case_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "support.json"
            first = open_support_case(order_id="ord_x", reason="blocked_fetch", requested_remedy="refund", support_path=path)
            second = open_support_case(order_id="ord_x", reason="blocked_fetch", requested_remedy="refund", support_path=path)
            self.assertEqual(first["case_id"], second["case_id"])
            self.assertEqual(len(json.loads(path.read_text())["cases"]), 1)


if __name__ == "__main__":
    unittest.main()
