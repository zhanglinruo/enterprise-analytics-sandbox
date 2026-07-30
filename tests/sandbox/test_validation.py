import sqlite3
import unittest

from ainative.sandbox.validation import SandboxValidator


class ValidationTest(unittest.TestCase):
    def test_unbalanced_voucher_is_blocking(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "create table fact_journal_entry "
            "(voucher_id text, debit_cents integer, credit_cents integer)"
        )
        conn.execute("insert into fact_journal_entry values ('V1', 100, 0)")

        report = SandboxValidator().validate_journals(conn)

        self.assertFalse(report.publishable)
        self.assertEqual("journal_unbalanced", report.issues[0].code)

    def test_valid_report_is_publishable(self):
        report = SandboxValidator.empty_report()

        self.assertTrue(report.publishable)

    def test_twenty_seeds_all_generate_publishable_data(self):
        from ainative.sandbox.service import build_golden_scenario

        for seed in range(20):
            result = build_golden_scenario(seed=seed)
            self.assertTrue(
                result.validation.publishable,
                (seed, result.validation.issues),
            )


if __name__ == "__main__":
    unittest.main()
