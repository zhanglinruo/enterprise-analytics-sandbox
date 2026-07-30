import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.master_data import MasterDataGenerator
from ainative.sandbox.schema import PUBLISHED_TABLES, create_database
from ainative.sandbox.spec import ScenarioSpec


class MasterDataTest(unittest.TestCase):
    def test_creates_exactly_fifteen_published_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = create_database(Path(tmp) / "exam.db")
            tables = {
                row[0]
                for row in conn.execute(
                    "select name from sqlite_master "
                    "where type='table' and name not like '\\_%' escape '\\'"
                )
            }

            self.assertEqual(15, len(PUBLISHED_TABLES))
            self.assertEqual(set(PUBLISHED_TABLES), tables)

    def test_populates_expected_master_data_and_valid_foreign_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = create_database(Path(tmp) / "exam.db")
            spec = ScenarioSpec.create("revenue_up_profit_down", seed=11)

            MasterDataGenerator(spec).populate(conn)

            self.assertEqual(
                100,
                conn.execute("select count(*) from dim_customer").fetchone()[0],
            )
            self.assertEqual(
                50,
                conn.execute("select count(*) from dim_supplier").fetchone()[0],
            )
            self.assertEqual(
                100,
                conn.execute("select count(*) from dim_product").fetchone()[0],
            )
            self.assertEqual([], conn.execute("pragma foreign_key_check").fetchall())


if __name__ == "__main__":
    unittest.main()
