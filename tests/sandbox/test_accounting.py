import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.accounting import AccountingProjector, financial_snapshot
from ainative.sandbox.events import EventSimulator, normal_parameters
from ainative.sandbox.master_data import MasterDataGenerator
from ainative.sandbox.schema import create_database
from ainative.sandbox.spec import ScenarioSpec


class AccountingTest(unittest.TestCase):
    def test_every_voucher_balances_and_inventory_reconciles(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = create_database(Path(tmp) / "exam.db")
            spec = ScenarioSpec.create("revenue_up_profit_down", seed=31)
            MasterDataGenerator(spec).populate(conn)
            events = EventSimulator(spec, normal_parameters).generate(conn)

            AccountingProjector().project(conn, events)

            unbalanced = conn.execute(
                """
                select voucher_id
                from fact_journal_entry
                group by voucher_id
                having sum(debit_cents) <> sum(credit_cents)
                """
            ).fetchall()
            negative_inventory = conn.execute(
                """
                select product_id
                from fact_inventory_movement
                group by product_id
                having sum(quantity) < 0
                """
            ).fetchall()
            self.assertEqual([], unbalanced)
            self.assertEqual([], negative_inventory)

    def test_snapshot_satisfies_accounting_equation(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = create_database(Path(tmp) / "exam.db")
            spec = ScenarioSpec.create("revenue_up_profit_down", seed=32)
            MasterDataGenerator(spec).populate(conn)
            events = EventSimulator(spec, normal_parameters).generate(conn)
            AccountingProjector().project(conn, events)

            snapshot = financial_snapshot(conn, "2025-12")

            self.assertEqual(
                snapshot.assets_cents,
                snapshot.liabilities_cents + snapshot.equity_cents,
            )


if __name__ == "__main__":
    unittest.main()
