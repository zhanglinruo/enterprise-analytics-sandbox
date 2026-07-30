import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.events import EventSimulator, normal_parameters
from ainative.sandbox.master_data import MasterDataGenerator
from ainative.sandbox.schema import create_database
from ainative.sandbox.spec import ScenarioSpec


class EventSimulatorTest(unittest.TestCase):
    def build(self, seed):
        tmp = tempfile.TemporaryDirectory()
        conn = create_database(Path(tmp.name) / "exam.db")
        spec = ScenarioSpec.create("revenue_up_profit_down", seed=seed)
        MasterDataGenerator(spec).populate(conn)
        return tmp, conn, spec

    def test_same_seed_produces_identical_events(self):
        left_tmp, left_conn, left_spec = self.build(21)
        right_tmp, right_conn, right_spec = self.build(21)
        try:
            left = EventSimulator(left_spec, normal_parameters).generate(left_conn)
            right = EventSimulator(right_spec, normal_parameters).generate(right_conn)
            self.assertEqual(left, right)
        finally:
            left_conn.close()
            right_conn.close()
            left_tmp.cleanup()
            right_tmp.cleanup()

    def test_events_cover_all_periods_and_have_positive_quantities(self):
        tmp, conn, spec = self.build(22)
        try:
            events = EventSimulator(spec, normal_parameters).generate(conn)
            self.assertEqual(set(spec.periods()), {event.period for event in events})
            self.assertTrue(
                all(
                    event.quantity > 0
                    for event in events
                    if event.quantity is not None
                )
            )
        finally:
            conn.close()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
