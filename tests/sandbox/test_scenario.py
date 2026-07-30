import unittest

from ainative.sandbox.events import normal_parameters
from ainative.sandbox.scenarios import load_scenario


class ScenarioTest(unittest.TestCase):
    def test_definition_contains_three_versioned_causes(self):
        definition = load_scenario("revenue_up_profit_down")

        self.assertEqual("1.0.0", definition.version)
        self.assertEqual(
            {
                "raw_material_price_increase",
                "low_margin_product_mix",
                "customer_discount_increase",
            },
            {cause.cause_id for cause in definition.causes},
        )
        self.assertAlmostEqual(
            1.0, sum(cause.contribution for cause in definition.causes)
        )

    def test_ground_truth_separates_proven_causes_and_unknowns(self):
        truth = load_scenario("revenue_up_profit_down").ground_truth()

        self.assertIn("customer_competition_strategy", truth.unknowns)
        self.assertIn("customer_loss", truth.forbidden_claims)

    def test_only_affected_periods_receive_operating_changes(self):
        definition = load_scenario("revenue_up_profit_down")
        normal = normal_parameters("2025-09")
        affected = normal_parameters("2025-10")

        self.assertEqual(normal, definition.parameters_for_period("2025-09", normal))
        changed = definition.parameters_for_period("2025-10", affected)
        self.assertGreater(changed.demand_multiplier, affected.demand_multiplier)
        self.assertGreater(
            changed.value_product_demand_share,
            affected.value_product_demand_share,
        )


if __name__ == "__main__":
    unittest.main()
