#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "operator"))

from shared_signals import (  # noqa: E402
    build_business_summary,
    connect_source_input,
    evaluate_worker_controls,
    join_action_outcome,
    record_hypothesis_cycle,
)


class SharedSignalsTests(unittest.TestCase):
    def test_join_and_changed_only_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.json"
            join_action_outcome(
                project_id="commercelint",
                action_id="act_1",
                action_summary="Validate sample intake",
                outcome_status="author_complete",
                source_coverage=["private_intake", "paid_report"],
                store_path=path,
            )
            first = connect_source_input(
                project_id="commercelint",
                source_name="production_smoke",
                metric_name="checks_passed",
                value=7,
                store_path=path,
            )
            second = connect_source_input(
                project_id="commercelint",
                source_name="production_smoke",
                metric_name="checks_passed",
                value=7,
                store_path=path,
            )
            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            summary = build_business_summary(store_path=path, summary_path=Path(tmp) / "summary.json")
            self.assertEqual(summary["action_count"], 1)
            self.assertEqual(summary["source_input_count"], 1)

    def test_two_project_hypotheses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.json"
            a = record_hypothesis_cycle(
                project_id="commercelint",
                hypothesis="Pre-charge URL rejection reduces invalid inquiries",
                change="Client+server URL batch validation",
                observation_window="7d",
                decision="continue",
                evidence=["tests/test_paid_intake_report.py"],
                store_path=path,
            )
            b = record_hypothesis_cycle(
                project_id="bidetfit",
                hypothesis="Manufacturer-sourced fit answers reduce unresolved checker exits",
                change="Publish two sourced answers without affiliate commission claims",
                observation_window="14d",
                decision="inconclusive",
                evidence=["H11 checker observation"],
                store_path=path,
            )
            self.assertNotEqual(a["id"], b["id"])
            store = json.loads(path.read_text())
            self.assertEqual(len(store["hypotheses"]), 2)

    def test_worker_controls(self):
        self.assertEqual(evaluate_worker_controls({"mode": "STOP"})["decision"], "stop")
        self.assertEqual(evaluate_worker_controls({"mode": "NO_OP"})["decision"], "no_op")
        self.assertEqual(
            evaluate_worker_controls({"mode": "RUN", "daily_action_budget": 1, "daily_actions_used": 1})["decision"],
            "budget_exhausted",
        )
        self.assertEqual(
            evaluate_worker_controls({"mode": "RUN", "max_task_retries": 2}, attempts=3)["decision"],
            "stop_retries",
        )
        self.assertTrue(evaluate_worker_controls({"mode": "RUN"})["allow_action"])


if __name__ == "__main__":
    unittest.main()
