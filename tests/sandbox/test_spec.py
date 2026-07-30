import unittest

from ainative.sandbox.spec import ScenarioSpec


class ScenarioSpecTest(unittest.TestCase):
    def test_creates_twelve_months_and_stable_benchmark_id(self):
        first = ScenarioSpec.create("revenue_up_profit_down", seed=20260730)
        second = ScenarioSpec.create("revenue_up_profit_down", seed=20260730)

        self.assertEqual("2025-01", first.periods()[0])
        self.assertEqual("2025-12", first.periods()[-1])
        self.assertEqual(12, len(first.periods()))
        self.assertEqual(first.benchmark_id, second.benchmark_id)

    def test_rejects_unknown_scenario(self):
        with self.assertRaisesRegex(ValueError, "Unsupported scenario"):
            ScenarioSpec.create("unknown", seed=1)

    def test_serialization_contains_version_and_seed(self):
        spec = ScenarioSpec.create("revenue_up_profit_down", seed=9)

        payload = spec.to_dict()

        self.assertEqual("1.0.0", payload["generator_version"])
        self.assertEqual(9, payload["seed"])


if __name__ == "__main__":
    unittest.main()
