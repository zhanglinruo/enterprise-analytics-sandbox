import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SandboxCliTest(unittest.TestCase):
    def test_generate_and_score_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generated = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ainative.cli",
                    "sandbox-generate",
                    "--seed",
                    "61",
                    "--output",
                    str(root / "exam"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            archive = Path(json.loads(generated.stdout)["archive"])
            self.assertTrue(archive.exists())

            from tests.sandbox.helpers import write_correct_answer

            correct_answer = write_correct_answer(
                root / "exam", root / "correct_answer.json"
            )
            scored = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ainative.cli",
                    "sandbox-score",
                    "--benchmark",
                    str(root / "exam"),
                    "--answer",
                    str(correct_answer),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            report = json.loads(scored.stdout)
            self.assertGreaterEqual(report["total_score"], 90)


if __name__ == "__main__":
    unittest.main()
