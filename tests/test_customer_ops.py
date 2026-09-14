#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "operator"))

from customer_ops import (  # noqa: E402
    PRIMANDIR_PORTAL,
    associate_order_support,
    build_event,
    deliver_outbox_once,
    enqueue_recovery,
    local_fixture_transporter,
    process_customer_event,
    refuse_primandir_for_commercelint,
    resolve_crm_destination,
    run_synthetic_inquiry_route,
    stage_operator_response,
    unavailable_live_transporter,
    upsert_crm_projection,
)


class CustomerOpsTests(unittest.TestCase):
    def test_commercelint_destination_excludes_primandir(self):
        route = resolve_crm_destination("commercelint")
        self.assertNotEqual(route["crm_destination"], PRIMANDIR_PORTAL)
        self.assertIn(PRIMANDIR_PORTAL, route["forbidden_crm_destinations"])
        with self.assertRaises(PermissionError):
            refuse_primandir_for_commercelint("commercelint", PRIMANDIR_PORTAL)

    def test_idempotent_outbox_replay(self):
        event = build_event(
            project_id="commercelint",
            event_type="inquiry.received",
            source_ref="private_intake",
            inquiry_reference="inq_abc",
            audience_consent_classification="support_inquiry_only",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "outbox.json"
            first = process_customer_event(event, contact_fingerprint="fp", outbox_path=path)
            second = process_customer_event(event, contact_fingerprint="fp", outbox_path=path)
            self.assertTrue(first["outbox_created"])
            self.assertFalse(second["outbox_created"])
            self.assertEqual(first["crm_record"]["status"], "projected_local")
            store = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(store["items"]), 1)
            self.assertEqual(store["items"][0]["slack"]["response_routing"]["mode"], "explicit_send_reply_action_required")

    def test_consent_skips_crm_upsert(self):
        event = build_event(
            project_id="commercelint",
            event_type="inquiry.received",
            source_ref="private_intake",
            inquiry_reference="inq_no_consent",
            audience_consent_classification="marketing_without_opt_in",
        )
        record = upsert_crm_projection(event, contact_fingerprint="fp")
        self.assertEqual(record["status"], "skipped_consent")

    def test_recovery_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recovery.json"
            first = enqueue_recovery("key1", "hubspot unavailable", recovery_path=path)
            second = enqueue_recovery("key1", "hubspot unavailable", recovery_path=path)
            self.assertEqual(first["idempotency_key"], second["idempotency_key"])
            self.assertEqual(len(json.loads(path.read_text())["items"]), 1)

    def test_deliver_outbox_and_live_unavailable_recovery(self):
        event = build_event(
            project_id="commercelint",
            event_type="inquiry.received",
            source_ref="private_intake",
            inquiry_reference="inq_deliver",
            audience_consent_classification="support_inquiry_only",
        )
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp) / "outbox.json"
            recovery = Path(tmp) / "recovery.json"
            process_customer_event(event, contact_fingerprint="fp", outbox_path=outbox)
            ok = deliver_outbox_once(outbox_path=outbox, transporter=local_fixture_transporter)
            self.assertTrue(ok["delivered"])
            self.assertFalse(ok["live"])
            # Second event for unavailable path
            event2 = build_event(
                project_id="commercelint",
                event_type="inquiry.received",
                source_ref="private_intake",
                inquiry_reference="inq_live_miss",
                audience_consent_classification="transactional_order_support",
            )
            process_customer_event(event2, contact_fingerprint="fp2", outbox_path=outbox)
            for _ in range(3):
                result = deliver_outbox_once(
                    outbox_path=outbox,
                    recovery_path=recovery,
                    transporter=unavailable_live_transporter,
                    max_attempts=3,
                )
            self.assertEqual(result["status"], "needs_recovery")
            self.assertEqual(len(json.loads(recovery.read_text())["items"]), 1)

    def test_operator_response_refuses_autosend(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "responses.json"
            with self.assertRaises(PermissionError):
                stage_operator_response(
                    idempotency_key="k1",
                    draft_body="Hello",
                    auto_send=True,
                    responses_path=path,
                )
            staged = stage_operator_response(
                idempotency_key="k1",
                draft_body="Hello customer (staged only).",
                responses_path=path,
            )
            self.assertFalse(staged["record"]["sent"])
            self.assertEqual(staged["record"]["status"], "staged_awaiting_explicit_send")

    def test_synthetic_full_route_replay_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            kwargs = dict(
                outbox_path=Path(tmp) / "outbox.json",
                recovery_path=Path(tmp) / "recovery.json",
                support_path=Path(tmp) / "support.json",
                responses_path=Path(tmp) / "responses.json",
            )
            first = run_synthetic_inquiry_route(
                inquiry_reference="inq_route_1",
                contact_fingerprint="fp_route",
                order_reference="ord_route_1",
                support_reference="sup_route_1",
                **kwargs,
            )
            second = run_synthetic_inquiry_route(
                inquiry_reference="inq_route_1",
                contact_fingerprint="fp_route",
                order_reference="ord_route_1",
                support_reference="sup_route_1",
                **kwargs,
            )
            self.assertFalse(first["live_crm_or_slack"])
            self.assertNotEqual(first["crm_destination"], PRIMANDIR_PORTAL)
            self.assertTrue(first["delivery"]["delivered"])
            self.assertFalse(second["processed"]["outbox_created"])
            support = associate_order_support(
                inquiry_reference="inq_route_1",
                order_reference="ord_route_1",
                support_reference="sup_route_1",
                support_path=kwargs["support_path"],
            )
            self.assertFalse(support["created"])


if __name__ == "__main__":
    unittest.main()
