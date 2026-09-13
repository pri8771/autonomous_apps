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
    append_outbox,
    build_event,
    enqueue_recovery,
    process_customer_event,
    refuse_primandir_for_commercelint,
    resolve_crm_destination,
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
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "outbox.json"
            first = process_customer_event(event, contact_fingerprint="fp", outbox_path=path)
            second = process_customer_event(event, contact_fingerprint="fp", outbox_path=path)
            self.assertTrue(first["outbox_created"])
            self.assertFalse(second["outbox_created"])
            store = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(store["items"]), 1)
            self.assertEqual(store["items"][0]["slack"]["response_routing"]["mode"], "explicit_send_reply_action_required")

    def test_recovery_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recovery.json"
            first = enqueue_recovery("key1", "hubspot unavailable", recovery_path=path)
            second = enqueue_recovery("key1", "hubspot unavailable", recovery_path=path)
            self.assertEqual(first["idempotency_key"], second["idempotency_key"])
            self.assertEqual(len(json.loads(path.read_text())["items"]), 1)


if __name__ == "__main__":
    unittest.main()
