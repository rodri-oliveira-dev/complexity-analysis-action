"""Contract tests for GitHub ruleset recipes; no GitHub API calls."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".github" / "rulesets"


class RepositoryRulesetsTests(unittest.TestCase):
    def setUp(self):
        self.main = json.loads((ROOT / "main.json").read_text(encoding="utf-8"))
        self.tags = json.loads((ROOT / "release-tags.json").read_text(encoding="utf-8"))

    def test_branch_policy(self):
        rules = {x["type"]: x for x in self.main["rules"]}
        self.assertEqual(self.main["target"], "branch")
        self.assertEqual(self.main["enforcement"], "active")
        self.assertEqual(self.main["bypass_actors"], [])
        self.assertEqual(self.main["conditions"]["ref_name"]["include"], ["~DEFAULT_BRANCH"])
        self.assertTrue({"deletion", "non_fast_forward", "required_linear_history", "pull_request", "required_status_checks"} <= rules.keys())
        self.assertEqual(rules["pull_request"]["parameters"]["required_approving_review_count"], 0)
        self.assertTrue(rules["pull_request"]["parameters"]["required_review_thread_resolution"])
        self.assertEqual(rules["pull_request"]["parameters"]["allowed_merge_methods"], ["squash", "rebase"])

    def test_require_actual_ci_jobs_only(self):
        req = self.main["rules"][-1]["parameters"]
        self.assertTrue(req["strict_required_status_checks_policy"])
        expected = {
            "static-validation", "script-integration",
            "Published CLI / pull-request regression",
            "Published CLI / csproj", "Published CLI / sln", "Published CLI / slnx",
            "quality-gates", "expected-errors", "analyze",
        }
        self.assertEqual({x["context"] for x in req["required_status_checks"]}, expected)
        self.assertEqual({x["integration_id"] for x in req["required_status_checks"]}, {15368})

    def test_release_tags_do_not_lock_major_alias(self):
        self.assertEqual(self.tags["target"], "tag")
        self.assertEqual(self.tags["enforcement"], "active")
        self.assertEqual(self.tags["bypass_actors"], [])
        pattern = self.tags["conditions"]["ref_name"]["include"]
        self.assertEqual(pattern, ["refs/tags/v*.*.*"])
        self.assertNotIn("~ALL", pattern)
        self.assertEqual({x["type"] for x in self.tags["rules"]}, {"deletion", "update"})
        self.assertNotIn("creation", {x["type"] for x in self.tags["rules"]})


if __name__ == "__main__":
    unittest.main()
