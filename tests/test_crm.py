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
        self.assertIsNone(record["potential_value_usd"])
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

    def test_replay_preserves_an_explicit_value_including_cents(self):
        crm = empty_crm()
        record, _ = upsert_public_github_lead(crm, self.payload(), at_utc="2026-09-13T16:00:00Z")
        record["potential_value_usd"] = 9.99
        record, _ = upsert_public_github_lead(crm, self.payload(), at_utc="2026-09-13T16:01:00Z")
        self.assertEqual(record["potential_value_usd"], 9.99)

    def test_unknown_values_are_excluded_and_total_is_incomplete(self):
        crm = empty_crm()
        upsert_public_github_lead(crm, self.payload(), at_utc="2026-09-13T16:00:00Z")
        aggregate = summary(crm)
        self.assertIsNone(aggregate["open_potential_value_usd"])
        self.assertIsNone(aggregate["known_open_potential_value_usd"])
        self.assertEqual(aggregate["open_unvalued_lead_count"], 1)
        payload = {**self.payload(), "id": "github-issue-43"}
        priced, _ = upsert_public_github_lead(crm, payload, at_utc="2026-09-13T16:00:00Z")
        priced["potential_value_usd"] = 9.99
        aggregate = summary(crm)
        self.assertIsNone(aggregate["open_potential_value_usd"])
        self.assertEqual(aggregate["known_open_potential_value_usd"], 9.99)
        self.assertFalse(aggregate["open_valuation_complete"])
        self.assertEqual(aggregate["open_valued_lead_count"], 1)

    def test_explicit_zero_and_decimal_values_remain_distinct_from_unknown(self):
        crm = empty_crm()
        record, _ = upsert_public_github_lead(crm, self.payload(), at_utc="2026-09-13T16:00:00Z")
        record["potential_value_usd"] = 0
        record, _ = upsert_public_github_lead(crm, self.payload(), at_utc="2026-09-13T16:01:00Z")
        self.assertEqual(record["potential_value_usd"], 0)
        self.assertEqual(summary(crm)["open_potential_value_usd"], 0)
        record["potential_value_usd"] = 9.99
        self.assertEqual(summary(crm)["open_potential_value_usd"], 9.99)
        record["stage"] = "lost"
        self.assertEqual(summary(crm)["open_valued_lead_count"], 0)

    def test_invalid_valuations_are_rejected(self):
        for value in [float("nan"), float("inf"), -1, True, "unverified"]:
            crm = empty_crm()
            record, _ = upsert_public_github_lead(crm, self.payload(), at_utc="2026-09-13T16:00:00Z")
            record["potential_value_usd"] = value
            with self.assertRaises(ValueError):
                summary(crm)

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
