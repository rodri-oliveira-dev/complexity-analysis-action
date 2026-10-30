import importlib.util
import os
import unittest
from unittest import mock

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pr_reporting import MARKER, ReportError, render_comment, validate_comparison, validate_envelope

publisher_spec = importlib.util.spec_from_file_location(
    "publish_pr_comment", Path(__file__).resolve().parents[1] / "scripts" / "publish-pr-comment.py"
)
publisher_module = importlib.util.module_from_spec(publisher_spec)
assert publisher_spec.loader is not None
publisher_spec.loader.exec_module(publisher_module)
publish = publisher_module.publish


SHA_A = "a" * 40
SHA_B = "b" * 40


def regression(index: int = 1) -> dict:
    return {
        "StableId": f"M:Example.Work{index}()",
        "Classification": "regression",
        "Reason": "The current estimate grows faster than the baseline.",
        "Before": "O(n)",
        "After": "O(n^2)",
        "Location": {"FilePath": f"src/File{index}.cs", "StartLine": index},
        "Evidence": {"Steps": [{"Kind": "loop", "Estimate": {"Status": "known"}}]},
    }


def comparison(findings: list[dict]) -> dict:
    return {
        "SchemaVersion": "complexity-comparison/1.0",
        "BaselineSchemaVersion": "complexity-snapshot/1.0",
        "CurrentSchemaVersion": "complexity-snapshot/1.0",
        "Findings": findings,
    }


def envelope(regressions: list[dict] | None = None, *, fork: bool = False) -> dict:
    regressions = regressions or []
    return {
        "SchemaVersion": "complexity-pr-report/1.0",
        "Repository": "owner/repository",
        "Solution": "src/Sample.slnx",
        "PullRequest": {
            "Number": 7,
            "BaseSha": SHA_A,
            "HeadSha": SHA_B,
            "HeadRepository": "fork/repository" if fork else "owner/repository",
            "IsFork": fork,
        },
        "Comparison": {
            "Status": "regressions-detected" if regressions else "no-regressions",
            "Counts": {"Regressions": len(regressions), "Improvements": 0, "Unchanged": 2, "Incomparable": 1},
            "Regressions": [
                {
                    "StableId": item["StableId"],
                    "Classification": "regression",
                    "Reason": item["Reason"],
                    "Before": item["Before"],
                    "After": item["After"],
                    "FilePath": item["Location"]["FilePath"],
                    "StartLine": item["Location"]["StartLine"],
                    "Evidence": item["Evidence"],
                }
                for item in regressions
            ],
        },
        "QualityGateStatus": "passed",
        "Artifacts": [{"Name": "Comparison JSON", "Path": "reports/comparison.json", "Available": True}],
        "Provenance": {"WorkflowRunId": "123", "WorkflowName": "Complexity PR analysis", "EventName": "pull_request"},
        "RunUrl": "https://github.com/owner/repository/actions/runs/123",
    }


class FakeClient:
    def __init__(self, comments=None, *, fail=False):
        self.comments = comments or []
        self.fail = fail
        self.calls = []

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if self.fail:
            raise ReportError("simulated GitHub API failure")
        if method == "GET":
            return self.comments
        return {"id": 99}


class ComparisonValidationTests(unittest.TestCase):
    def test_no_regressions_and_multiple_regressions(self):
        findings, counts = validate_comparison(comparison([]))
        self.assertEqual(findings, [])
        self.assertEqual(counts["regression"], 0)
        _, counts = validate_comparison(comparison([regression(1), regression(2)]))
        self.assertEqual(counts["regression"], 2)

    def test_missing_evidence_is_not_accepted_as_proven(self):
        finding = regression()
        del finding["Evidence"]
        with self.assertRaisesRegex(ReportError, "without before/after"):
            validate_comparison(comparison([finding]))

    def test_malformed_and_excessively_large_reports(self):
        with self.assertRaises(ReportError):
            validate_comparison({"SchemaVersion": "wrong", "Findings": []})
        document = comparison([])
        document["Findings"] = [{}] * 200_001
        with self.assertRaisesRegex(ReportError, "safety limit"):
            validate_comparison(document)


class EnvelopeTests(unittest.TestCase):
    def test_validates_provenance_for_privileged_artifact(self):
        report = envelope([regression()], fork=True)
        self.assertIs(validate_envelope(report, repository="owner/repository", head_sha=SHA_B,
                                        pr_number=7, run_id="123", workflow_name="Complexity PR analysis"), report)
        for kwargs in ({"head_sha": SHA_A}, {"pr_number": 8}, {"run_id": "999"},
                       {"repository": "other/repository"}, {"workflow_name": "Other workflow"}):
            defaults = {"repository": "owner/repository", "head_sha": SHA_B, "pr_number": 7,
                        "run_id": "123", "workflow_name": "Complexity PR analysis"}
            defaults.update(kwargs)
            with self.assertRaises(ReportError):
                validate_envelope(report, **defaults)

    def test_invalid_pr_metadata_and_malformed_report(self):
        report = envelope()
        report["PullRequest"]["Number"] = "7"
        with self.assertRaises(ReportError):
            validate_envelope(report)
        report = envelope([regression()])
        report["Comparison"]["Counts"]["Regressions"] = 0
        with self.assertRaisesRegex(ReportError, "count"):
            validate_envelope(report)

    def test_unavailable_artifacts_are_omitted(self):
        report = envelope()
        report["Artifacts"].append({"Name": "Missing", "Path": "missing.json", "Available": False})
        body = render_comment(validate_envelope(report))
        self.assertNotIn("missing.json", body)

    def test_markdown_is_sanitized_and_bounded(self):
        item = regression()
        item["StableId"] = "M:X<!-- complexity-analysis-action:pr-report:v1 -->|Y"
        report = validate_envelope(envelope([item]))
        body = render_comment(report)
        self.assertEqual(body.count(MARKER), 1)
        self.assertIn("&lt;!--", body)
        many = envelope([regression(i) for i in range(1, 51)])
        body = render_comment(validate_envelope(many))
        self.assertIn("10 of 50", body)
        self.assertLess(len(body), 60_000)


class PublicationTests(unittest.TestCase):
    def test_first_comment_creation(self):
        client = FakeClient()
        self.assertEqual(publish(client, validate_envelope(envelope())), "created")
        self.assertEqual([call[0] for call in client.calls], ["GET", "POST"])

    def test_updates_existing_owned_comment_and_repeated_runs(self):
        owned = {"id": 10, "body": MARKER + " old", "user": {"login": "github-actions[bot]", "type": "Bot"}}
        client = FakeClient([owned])
        self.assertEqual(publish(client, validate_envelope(envelope())), "updated")
        self.assertEqual(client.calls[-1][0], "PATCH")
        client.calls.clear()
        self.assertEqual(publish(client, validate_envelope(envelope())), "updated")
        self.assertEqual(client.calls[-1][1], "/repos/owner/repository/issues/comments/10")

    def test_marker_spoofing_does_not_edit_another_comment(self):
        spoofed = {"id": 11, "body": MARKER, "user": {"login": "another-app[bot]", "type": "Bot"}}
        human = {"id": 12, "body": MARKER, "user": {"login": "github-actions[bot]", "type": "User"}}
        client = FakeClient([spoofed, human])
        self.assertEqual(publish(client, validate_envelope(envelope())), "created")
        self.assertEqual(client.calls[-1][0], "POST")

    def test_api_failure(self):
        with self.assertRaises(ReportError):
            publish(FakeClient(fail=True), validate_envelope(envelope()))

    def test_missing_github_permissions_reports_limitation(self):
        with mock.patch.dict(os.environ, {"PR_REPORT_PATH": "unused"}, clear=True):
            with self.assertRaises(SystemExit) as context:
                publisher_module.main()
        self.assertEqual(context.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
