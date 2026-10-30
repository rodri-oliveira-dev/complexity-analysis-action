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
        self.assertFalse(result["marketplacePublished"])

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
