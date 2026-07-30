import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from ainative.sandbox.packaging import ExamPackageBuilder
from ainative.sandbox.service import build_golden_scenario


class PackagingTest(unittest.TestCase):
    def test_package_contains_public_assets_and_no_ground_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_golden_scenario(seed=51, output_dir=root / "work")

            archive = ExamPackageBuilder().build(result, root / "out")

            with zipfile.ZipFile(archive) as package:
                names = set(package.namelist())
                self.assertIn("data/enterprise.db", names)
                self.assertIn("schema/data_dictionary.md", names)
                self.assertIn("semantic/metrics.json", names)
                self.assertIn("task/analysis_question.md", names)
                self.assertIn("manifest.json", names)
                self.assertFalse(any("ground_truth" in name for name in names))
                combined = b"".join(
                    package.read(name)
                    for name in names
                    if not name.endswith(".db")
                )
                self.assertNotIn(b"raw_material_price_increase", combined)

    def test_manifest_has_lineage_versions_and_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_golden_scenario(seed=52, output_dir=root / "work")

            archive = ExamPackageBuilder().build(result, root / "out")

            with zipfile.ZipFile(archive) as package:
                manifest = json.loads(package.read("manifest.json"))
                self.assertEqual(
                    result.spec.benchmark_id, manifest["benchmark_id"]
                )
                self.assertEqual(
                    result.database_sha256, manifest["database_sha256"]
                )
                self.assertEqual("1.0.0", manifest["generator_version"])


if __name__ == "__main__":
    unittest.main()
