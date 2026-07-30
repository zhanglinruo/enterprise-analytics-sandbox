import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.service import build_golden_scenario


class SandboxServiceTest(unittest.TestCase):
    def test_builds_publishable_reproducible_benchmark(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            first = build_golden_scenario(seed=41, output_dir=Path(left))
            second = build_golden_scenario(seed=41, output_dir=Path(right))

            self.assertTrue(first.validation.publishable)
            self.assertEqual(first.spec.benchmark_id, second.spec.benchmark_id)
            self.assertEqual(first.database_sha256, second.database_sha256)
            self.assertEqual(
                {
                    "raw_material_price_increase",
                    "low_margin_product_mix",
                    "customer_discount_increase",
                },
                set(first.ground_truth.root_causes),
            )


if __name__ == "__main__":
    unittest.main()
