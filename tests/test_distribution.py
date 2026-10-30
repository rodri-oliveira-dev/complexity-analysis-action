import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


distribution = load("validate_distribution", "scripts/validate-distribution.py")
required_runs = load("check_required_runs", "scripts/check-required-runs.py")


class DistributionTests(unittest.TestCase):
    def test_repository_distribution_contract(self):
        result = distribution.validate(ROOT)
        self.assertEqual(result["actionName"], "Complexity Analysis")
        self.assertEqual(result["categories"], ["code-quality", "continuous-integration"])
        self.assertEqual(result["marketplaceListingVerification"], "not-verified-by-local-validator")
        self.assertNotIn("marketplacePublished", result)

    def test_published_release_documentation_is_usable(self):
        release_ref = (
            "rodri-oliveira-dev/complexity-analysis-action@"
            "2d807ef29ca03c685d224543a135d8c30dfe2c67"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        portuguese = (ROOT / "README.pt-BR.md").read_text(encoding="utf-8")
        marketplace = (ROOT / "docs" / "marketplace.md").read_text(encoding="utf-8")
        self.assertIn("[![GitHub Action]", readme.split("## Overview", 1)[0])
        self.assertIn("## Quick start", readme)
        self.assertIn(".github/workflows/complexity-analysis.yml", readme)
        for document in (readme, portuguese):
            self.assertIn(release_ref, document)
            self.assertNotIn("@REVIEWED_FULL_40_CHARACTER_SHA", document)
            self.assertNotIn("@0000000000000000000000000000000000000000", document)
        self.assertIn("v1.0.0", readme)
        self.assertIn("v1.0.0", portuguese)
        self.assertIn("Marketplace listing", marketplace)
        self.assertIn("not yet", marketplace)

    def test_copyable_examples_pin_published_release_commit(self):
        expected = "2d807ef29ca03c685d224543a135d8c30dfe2c67"
        for path in sorted((ROOT / "examples").glob("*.yml")):
            with self.subTest(example=path.name):
                content = path.read_text(encoding="utf-8")
                self.assertIn("@" + expected, content)
                self.assertNotIn("@0000000000000000000000000000000000000000", content)

    def test_latest_required_run_wins(self):
        runs = [
            {"name": "CI", "conclusion": "success", "created_at": "2026-01-01T00:00:00Z"},
            {"name": "CI", "conclusion": "failure", "created_at": "2026-01-02T00:00:00Z"},
            {"name": "CodeQL", "conclusion": "success", "created_at": "2026-01-01T00:00:00Z"},
        ]
        selected = required_runs.latest_by_workflow(runs)
        self.assertEqual(selected["CI"]["conclusion"], "failure")
        self.assertEqual(selected["CodeQL"]["conclusion"], "success")


if __name__ == "__main__":
    unittest.main()
