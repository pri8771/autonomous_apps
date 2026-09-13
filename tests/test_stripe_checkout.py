"""Provider contract and crash/replay tests. All Stripe/DNS/HTTP I/O is fake."""
from __future__ import annotations

import copy
import hashlib
import hmac
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "operator"))
import stripe_checkout as sc
from private_intake import validate_intake_request

NOW = 1800000000
WEBHOOK_SECRET = "whsec_testfixtureonly"


class FakeStripe:
    def __init__(self):
        self.calls = []
        self.sessions = {}
        self.original_fields = {}
        self.fail_once = False

    def __call__(self, fields, headers):
        self.calls.append((dict(fields), dict(headers)))
        key = headers["Idempotency-Key"]
        if key in self.original_fields and fields != self.original_fields[key]:
            raise sc.ProviderUnavailable("Stripe refuses changed parameters for an idempotency key")
        self.original_fields[key] = dict(fields)
        if key not in self.sessions:
            mode = "test" if "_test_" in headers["Authorization"] else "live"
            self.sessions[key] = {
                "object": "checkout.session", "id": f"cs_{mode}_" + hashlib.sha256(key.encode()).hexdigest()[:24],
                "livemode": mode == "live", "mode": fields["mode"],
                "client_reference_id": fields["client_reference_id"],
                "metadata": {"order_id": fields["metadata[order_id]"], "plan_id": fields["metadata[plan_id]"], "project_id": fields["metadata[project_id]"]},
                "amount_total": int(fields["line_items[0][price_data][unit_amount]"]),
                "currency": fields["line_items[0][price_data][currency]"],
                "url": "https://checkout.stripe.com/c/pay/providerfixture",
                "status": "open", "payment_status": "unpaid",
            }
        if self.fail_once:
            self.fail_once = False
            raise sc.ProviderUnavailable("Synthetic lost response after provider creation")
        return copy.deepcopy(self.sessions[key])


def sign(event, *, timestamp=NOW, secret=WEBHOOK_SECRET):
    raw = json.dumps(event, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), str(timestamp).encode() + b"." + raw, hashlib.sha256).hexdigest()
    return raw, f"t={timestamp},v1={signature}"


class StripeCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = sc.StripeConfig("test", "sk_test_fixture", WEBHOOK_SECRET, Path(self.tmp.name) / "test.sqlite",
            "https://priyanshchordia.com/commercelint/inquiry.html?payment=return",
            "https://priyanshchordia.com/commercelint/inquiry.html?payment=cancel")
        self.provider = FakeStripe()
        self.client = sc.StripeCheckout(self.config, transport=self.provider, clock=lambda: NOW)
        def without_dns(**kwargs):
            kwargs["resolve_dns"] = False
            return validate_intake_request(**kwargs)
        patcher = patch.object(sc, "validate_intake_request", side_effect=without_dns)
        patcher.start()
        self.addCleanup(patcher.stop)

    def create(self, plan="sample", **changes):
        args = {"request_id": "request-0000000001", "plan_id": plan,
                "urls": ["https://example.com/product"], "contact_email": "buyer@example.com"}
        args.update(changes)
        return self.client.create_checkout(**args)

    def event(self, *, event_id="evt_fixture1", kind="checkout.session.completed", paid=True):
        session = copy.deepcopy(next(iter(self.provider.sessions.values())))
        session.update(status="complete", payment_status="paid" if paid else "unpaid")
        return {"id": event_id, "object": "event", "type": kind, "livemode": False, "data": {"object": session}}

    def count(self, table):
        with closing(sqlite3.connect(self.config.database_path)) as db:
            return db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]

    def test_exact_one_time_tiers_and_no_recurrence(self):
        for plan, cents in sc.AMOUNTS.items():
            with self.subTest(plan=plan):
                result = self.create(plan, request_id="request-00000000-" + plan)
                fields, headers = self.provider.calls[-1]
                self.assertEqual(fields["mode"], "payment")
                self.assertEqual(fields["line_items[0][price_data][unit_amount]"], str(cents))
                self.assertEqual(fields["line_items[0][quantity]"], "1")
                self.assertFalse(any("recurring" in k for k in fields))
                self.assertTrue(headers["Idempotency-Key"].startswith("commercelint:test:"))
                self.assertEqual(result["payment_state"], "pending_checkout")
        self.assertEqual(self.count("jobs"), 0)

    def test_bad_intake_does_not_call_stripe(self):
        for kwargs in [{"urls": ["http://localhost/private"]}, {"claimed_price": 0.01},
                       {"contact_email": "invalid"}, {"plan_id": "subscription"}, {"request_id": []}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(sc.PaymentError):
                self.create(**kwargs)
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(self.count("orders"), 0)

    def test_retry_after_lost_response_reuses_provider_key(self):
        self.provider.fail_once = True
        with self.assertRaises(sc.ProviderUnavailable):
            self.create()
        first = self.create()
        again = self.create()
        self.assertEqual(first["session_id"], again["session_id"])
        self.assertEqual(len(self.provider.sessions), 1)
        self.assertEqual(len(self.provider.calls), 2)
        self.assertEqual(self.provider.calls[0][1], self.provider.calls[1][1])
        with self.assertRaises(sc.PaymentError):
            self.create(urls=["https://example.com/changed"])

    def test_uncertain_creation_after_idempotency_window_requires_reconciliation(self):
        self.provider.fail_once = True
        with self.assertRaises(sc.ProviderUnavailable):
            self.create()
        self.client.clock = lambda: NOW + 24 * 3600
        with self.assertRaises(sc.PaymentError):
            self.create()
        self.assertEqual(len(self.provider.calls), 1)

    def test_lost_response_replays_exact_original_fields_after_input_and_config_drift(self):
        self.provider.fail_once = True
        with self.assertRaises(sc.ProviderUnavailable):
            self.create(contact_email="Buyer@example.com")
        self.client.config = replace(self.config, success_url="https://priyanshchordia.com/commercelint/new-return.html")
        result = self.create(contact_email="buyer@example.com")
        self.assertEqual(result["payment_state"], "pending_checkout")
        self.assertEqual(self.provider.calls[0][0], self.provider.calls[1][0])
        self.assertEqual(len(self.provider.sessions), 1)

    def test_nonfinite_or_unrepresentable_price_returns_400_before_mutation(self):
        app = sc.create_wsgi_app(self.client)
        for price in ("NaN", "Infinity", "1e999999", {"bad": "price"}):
            body = json.dumps({"request_id": "request-0000000001", "plan_id": "sample", "urls": ["https://example.com/product"],
                               "contact_email": "buyer@example.com", "claimed_price": price}).encode()
            status = []
            response = app({"PATH_INFO": "/checkout", "REQUEST_METHOD": "POST", "CONTENT_LENGTH": str(len(body)),
                           "CONTENT_TYPE": "application/json", "HTTP_ORIGIN": "https://priyanshchordia.com", "wsgi.input": io.BytesIO(body)},
                           lambda s, headers: status.append(s))
            self.assertEqual(status, ["400 Bad Request"])
            self.assertIn("error", json.loads(b"".join(response)))
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(self.count("orders"), 0)

    def test_real_signature_format_tolerance_rotation_and_raw_bytes(self):
        self.create()
        raw, signature = sign(self.event())
        rotated = signature.replace(",v1=", ",v1=" + "0" * 64 + ",v1=")
        self.assertEqual(sc.verify_stripe_event(raw, rotated, WEBHOOK_SECRET, now=NOW)["id"], "evt_fixture1")
        for body, header in [(raw + b" ", signature), (raw, "sha256=" + "0" * 64),
                             sign(self.event(), timestamp=NOW - 301), sign(self.event(), timestamp=NOW + 301),
                             (raw, signature + f",t={NOW}")]:
            with self.assertRaises(sc.PaymentError):
                self.client.handle_webhook(body, header)
        self.assertEqual(self.count("events"), 0)

    def test_paid_receipt_is_atomic_and_concurrent_replay_enqueues_one_job(self):
        self.create()
        raw, signature = sign(self.event())
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.client.handle_webhook(raw, signature), range(8)))
        self.assertEqual(sum(not x["duplicate"] for x in results), 1)
        self.assertEqual(self.count("events"), 1)
        self.assertEqual(self.count("jobs"), 1)
        self.client.handle_webhook(*sign(self.event(event_id="evt_fixture2")))
        self.assertEqual(self.count("jobs"), 1)
        self.assertFalse(results[0].get("revenue_verified", False))

    def test_failed_job_insert_rolls_back_payment_and_event_for_retry(self):
        self.create()
        with closing(sqlite3.connect(self.config.database_path)) as db:
            db.execute("CREATE TRIGGER fail_job BEFORE INSERT ON jobs BEGIN SELECT RAISE(ABORT, 'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.client.handle_webhook(*sign(self.event()))
        self.assertEqual(self.count("events"), 0)
        with closing(sqlite3.connect(self.config.database_path)) as db:
            self.assertEqual(db.execute("SELECT payment_state FROM orders").fetchone()[0], "pending_checkout")
            db.execute("DROP TRIGGER fail_job")
        self.client.handle_webhook(*sign(self.event()))
        self.assertEqual(self.count("jobs"), 1)

    def test_mode_currency_amount_session_and_order_binding(self):
        self.create()
        mutations = [{"livemode": True}, {"currency": "eur"}, {"amount_total": 1},
                     {"amount_total": True}, {"id": "cs_test_wrong"}, {"mode": "subscription"},
                     {"client_reference_id": "ord_" + "0" * 32}, {"metadata": {}}]
        for mutation in mutations:
            event = self.event()
            event["data"]["object"].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(sc.PaymentError):
                self.client.handle_webhook(*sign(event))
        event = self.event()
        event["livemode"] = True
        with self.assertRaises(sc.PaymentError):
            self.client.handle_webhook(*sign(event))
        self.assertEqual(self.count("jobs"), 0)

    def test_unpaid_completion_waits_and_late_failure_does_not_regress_payment(self):
        self.create()
        self.client.handle_webhook(*sign(self.event(paid=False)))
        self.assertEqual(self.count("jobs"), 0)
        result = self.client.handle_webhook(*sign(self.event(event_id="evt_async", kind="checkout.session.async_payment_succeeded")))
        self.assertEqual(result["payment_state"], "succeeded")
        late = self.event(event_id="evt_late", kind="checkout.session.async_payment_failed", paid=False)
        self.client.handle_webhook(*sign(late))
        self.assertEqual(self.create()["payment_state"], "succeeded")
        self.assertEqual(self.count("jobs"), 1)

    def test_same_database_cannot_be_reused_across_modes(self):
        with self.assertRaises(sc.PaymentError):
            sc.StripeConfig("live", "sk_test_fixture", WEBHOOK_SECRET, self.config.database_path,
                            self.config.success_url, self.config.cancel_url)
        live = sc.StripeConfig("live", "sk_live_fixture", WEBHOOK_SECRET, self.config.database_path,
                               self.config.success_url, self.config.cancel_url)
        with self.assertRaises(sc.PaymentError):
            sc.StripeCheckout(live, transport=self.provider)
        self.assertNotIn("sk_test_fixture", repr(self.config))
        with self.assertRaises(sc.PaymentError):
            sc.StripeConfig("test", "sk_test_fixture", WEBHOOK_SECRET, ROOT / "state/payments.sqlite",
                            self.config.success_url, self.config.cancel_url)

    def test_paid_report_stages_privately_once_and_never_claims_delivery(self):
        order = self.create()
        html = (ROOT / "tests/fixtures/strong.html").read_text()
        pages = [{"url": "https://example.com/product", "html": html}]
        with self.assertRaises(sc.PaymentError):
            self.client.stage_report(order["order_id"], pages)
        self.client.handle_webhook(*sign(self.event()))
        with self.assertRaises(sc.PaymentError):
            self.client.stage_report(order["order_id"], [{"url": "https://example.com/other", "html": html}])
        first = self.client.stage_report(order["order_id"], pages)
        again = self.client.stage_report(order["order_id"], pages)
        self.assertEqual(first["report_sha256"], again["report_sha256"])
        self.assertTrue(again["duplicate"])
        self.assertEqual(first["delivery_status"], "not_delivered")
        with closing(sqlite3.connect(self.config.database_path)) as db:
            self.assertIn("CommerceLint", db.execute("SELECT report_markdown FROM jobs").fetchone()[0])

    def test_webhook_before_session_binding_retries_without_consuming_event(self):
        self.provider.fail_once = True
        with self.assertRaises(sc.ProviderUnavailable):
            self.create()
        event = self.event()
        with self.assertRaises(sc.ProviderUnavailable):
            self.client.handle_webhook(*sign(event))
        self.assertEqual(self.count("events"), 0)
        self.create()
        self.client.handle_webhook(*sign(event))
        restarted = sc.StripeCheckout(self.config, transport=self.provider, clock=lambda: NOW)
        self.assertTrue(restarted.handle_webhook(*sign(event))["duplicate"])
        self.assertEqual(self.count("jobs"), 1)

    def test_other_product_event_is_acknowledged_without_payment_mutation(self):
        self.create()
        event = self.event()
        event["data"]["object"]["metadata"]["project_id"] = "different-product"
        self.assertTrue(self.client.handle_webhook(*sign(event))["ignored"])
        self.assertEqual(self.count("events"), 0)
        self.assertEqual(self.count("jobs"), 0)

    def test_http_transport_calls_only_stripe_with_bounded_post(self):
        fake_response = unittest.mock.MagicMock()
        fake_response.__enter__.return_value.read.return_value = b'{"id":"cs_test_fixture"}'
        opener = unittest.mock.Mock()
        opener.open.return_value = fake_response
        with patch.object(sc, "build_opener", return_value=opener):
            sc.stripe_post({"mode": "payment"}, {"Authorization": "Bearer sk_test_fixture"})
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.stripe.com/v1/checkout/sessions")
        self.assertEqual(request.method, "POST")
        self.assertEqual(parse_qs(request.data.decode()), {"mode": ["payment"]})
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 20)
        fake_response.__enter__.return_value.read.assert_called_once_with(sc.MAX_BODY + 1)

    def test_wsgi_raw_webhook_and_rejects_caller_credentials(self):
        app = sc.create_wsgi_app(self.client)
        def invoke(path, body, **headers):
            captured = []
            environ = {"PATH_INFO": path, "REQUEST_METHOD": "POST", "CONTENT_LENGTH": str(len(body)),
                       "CONTENT_TYPE": "application/json", "wsgi.input": io.BytesIO(body), **headers}
            result = b"".join(app(environ, lambda status, hdr: captured.append(status)))
            return captured[0], json.loads(result)
        fields = {"request_id": "request-0000000001", "plan_id": "sample", "urls": ["https://example.com/product"], "contact_email": "buyer@example.com"}
        status, created = invoke("/checkout", json.dumps(fields).encode(), HTTP_ORIGIN="https://priyanshchordia.com")
        self.assertEqual(status, "200 OK")
        fields["api_key"] = "caller_must_not_supply"
        self.assertEqual(invoke("/checkout", json.dumps(fields).encode(), HTTP_ORIGIN="https://priyanshchordia.com")[0], "400 Bad Request")
        raw, signature = sign(self.event())
        self.assertEqual(invoke("/webhook", raw, HTTP_STRIPE_SIGNATURE=signature)[0], "200 OK")
        self.assertEqual(invoke("/webhook", raw, HTTP_STRIPE_SIGNATURE="invalid")[0], "400 Bad Request")
        self.assertEqual(self.count("jobs"), 1)


if __name__ == "__main__":
    unittest.main()
