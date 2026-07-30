import json
import tempfile
import unittest
from pathlib import Path

from ainative.sandbox.scoring import AgentAnswer, DeterministicScorer
from ainative.sandbox.service import build_golden_scenario
from tests.sandbox.helpers import build_correct_answer


FIXTURES = Path(__file__).parent / "fixtures"


class ScoringTest(unittest.TestCase):
    def test_correct_answer_scores_at_least_ninety(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_golden_scenario(seed=61, output_dir=Path(tmp))
            answer = AgentAnswer.from_dict(build_correct_answer(result))

            report = DeterministicScorer().score_database(answer, result)

            self.assertGreaterEqual(report.total_score, 90)
            self.assertEqual(0, len(report.unsupported_claims))

    def test_hallucinated_cause_is_reported_and_capped_below_sixty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_golden_scenario(seed=61, output_dir=Path(tmp))
            answer = AgentAnswer.from_dict(
                json.loads(
                    (FIXTURES / "hallucinated_answer.json").read_text(
                        encoding="utf-8"
                    )
                )
            )

            report = DeterministicScorer().score_database(answer, result)

            self.assertLess(report.total_score, 60)
            self.assertIn(
                "competitor_price_war", report.unsupported_claims
            )


if __name__ == "__main__":
    unittest.main()
