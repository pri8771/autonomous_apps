import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

OPERATOR = Path(__file__).resolve().parents[1] / "operator"
sys.path.insert(0, str(OPERATOR))
SPEC = importlib.util.spec_from_file_location("tested_lead_intake", OPERATOR / "lead_intake.py")
intake = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(intake)


class LeadIntakeTests(unittest.TestCase):
    def run_request(self, root, *, trial=False):
        event = {
            "repository": {"owner": {"login": "owner"}},
            "issue": {
                "number": 1, "user": {"login": "owner" if trial else "customer"},
                "title": "[CommerceLint request] " + ("[owner trial] " if trial else "") + "sample",
                "body": "### Public store URL\n\nhttps://example.com/\n",
                "html_url": "https://github.com/owner/repo/issues/1",
            },
        }
        event_path = root / "event.json"
        event_path.write_text(json.dumps(event), encoding="utf-8")
        with patch.object(intake, "STATE_PATH", root / "state.json"), \
             patch.object(intake, "LEADS_PATH", root / "leads.json"), \
             patch.object(intake, "CRM_PATH", root / "crm.json"), \
             patch.object(intake, "normalized_public_url", return_value="https://example.com/"), \
             patch.object(intake, "preliminary_findings", return_value=([{"check": "Public retrieval", "result": "Pass", "evidence": "HTTP 200", "next_step": "Review"}], {})), \
             patch.object(intake, "record_event"), \
             patch.object(sys, "argv", ["intake", "--event", str(event_path), "--comment-output", str(root / "comment.md")]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(intake.main(), 0)

    def test_owner_trial_replay_preserves_customer_metrics_and_crm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metrics = {"lead_requests": 3, "qualified_leads": 2, "gross_revenue_usd": 0}
            (root / "state.json").write_text(json.dumps({"metrics": metrics}))
            self.run_request(root, trial=True)
            self.run_request(root, trial=True)
            records = json.loads((root / "leads.json").read_text())
            self.assertEqual(records["leads"], [])
            self.assertEqual(len(records["owner_trials"]), 1)
            self.assertFalse(records["owner_trials"][0]["qualified"])
            self.assertTrue(records["owner_trials"][0]["url_accepted"])
            self.assertEqual(json.loads((root / "crm.json").read_text())["leads"], [])
            self.assertEqual(json.loads((root / "state.json").read_text())["metrics"], metrics)
            self.assertIn("not a customer lead", (root / "comment.md").read_text())

    def test_real_request_is_still_recorded_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_request(root)
            self.run_request(root)
            state = json.loads((root / "state.json").read_text())
            self.assertEqual(state["metrics"]["qualified_leads"], 1)
            self.assertEqual(state["metrics"]["lead_requests"], 1)
            self.assertEqual(len(json.loads((root / "crm.json").read_text())["leads"]), 1)

    def test_raw_script_policy_words_cannot_pass(self):
        page = '<script>const x={shippingType:"shipping",faq:"What is your return policy?"}</script>'
        with patch.object(intake, "fetch_public_html", return_value=("https://example.com/", page, 200)):
            findings, _ = intake.preliminary_findings("https://example.com/")
        policy = next(x for x in findings if x["check"] == "Policies")
        self.assertEqual(policy["result"], "Review")
        self.assertIn("No shipping", policy["evidence"])

    def test_link_presence_does_not_claim_policy_contents_verified(self):
        page = '<a href="/policies/shipping-policy">Shipping</a><a href="/returns">Returns</a>'
        with patch.object(intake, "fetch_public_html", return_value=("https://example.com/", page, 200)):
            findings, _ = intake.preliminary_findings("https://example.com/")
        policy = next(x for x in findings if x["check"] == "Policies")
        self.assertEqual(policy["result"], "Review")
        self.assertIn("2 possible policy link(s)", policy["evidence"])
        self.assertIn("not inspected", policy["evidence"])
