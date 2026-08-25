import importlib.util
import unittest
from pathlib import Path


CRM_PATH = Path(__file__).resolve().parents[1] / "operator" / "crm.py"
SPEC = importlib.util.spec_from_file_location("commercelint_crm", CRM_PATH)
crm_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(crm_module)
empty_crm = crm_module.empty_crm
summary = crm_module.summary
upsert_public_github_lead = crm_module.upsert_public_github_lead
validate_crm = crm_module.validate_crm


class CrmTests(unittest.TestCase):
    def payload(self):
        return {
            "id": "github-issue-42",
            "issue_url": "https://github.com/pri8771/autonomous_apps/issues/42",
            "github_user": "example-user",
            "created_at_utc": "2026-08-25T15:00:00Z",
            "store_url": "https://example.com/product/widget",
            "role": "Agency or consultant",
            "platform": "WooCommerce",
            "main_goal": "Variants and identifiers",
            "qualified": True,
        }

    def test_public_issue_is_projected_into_actionable_crm_record(self):
        crm = empty_crm()
        record, is_new = upsert_public_github_lead(
            crm, self.payload(), at_utc="2026-08-25T15:01:00Z"
        )
        self.assertTrue(is_new)
        self.assertEqual(record["stage"], "new")
        self.assertEqual(record["potential_value_usd"], 49)
        self.assertEqual(record["next_action"], "Review first pass and confirm scope")
        self.assertEqual(record["privacy_classification"], "public_source_only")
        self.assertNotIn("email", record)
        self.assertEqual(summary(crm)["lead_count"], 1)

    def test_replay_is_idempotent(self):
        crm = empty_crm()
        upsert_public_github_lead(crm, self.payload(), at_utc="2026-08-25T15:01:00Z")
        _, is_new = upsert_public_github_lead(
            crm, self.payload(), at_utc="2026-08-25T15:02:00Z"
        )
        self.assertFalse(is_new)
        self.assertEqual(len(crm["leads"]), 1)
        self.assertEqual(len(crm["activities"]), 1)
        self.assertEqual(crm["updated_at_utc"], "2026-08-25T15:01:00Z")

    def test_private_fields_are_rejected_from_public_ledger(self):
        crm = empty_crm()
        record, _ = upsert_public_github_lead(
            crm, self.payload(), at_utc="2026-08-25T15:01:00Z"
        )
        record["contact_email"] = "private@example.com"
        with self.assertRaises(ValueError):
            validate_crm(crm)


if __name__ == "__main__":
    unittest.main()
