import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "scripts" / "validate-report.py"


class ReportValidationTests(unittest.TestCase):
    def validate(self, kind: str, document: object, *extra: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / f"report.{kind}"
            report.write_text(json.dumps(document), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), kind, str(report), *extra],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_valid_json_report(self) -> None:
        report = {
            "SchemaVersion": "1.0",
            "EntryPoint": "Sample.csproj",
            "Projects": [{"Name": "Sample", "Path": "Sample.csproj", "Files": []}],
            "QualityGates": [
                {"Metric": "nloc", "Subject": "M", "Threshold": "10", "Actual": "2", "Passed": True}
            ],
        }
        self.assertEqual(self.validate("json", report).returncode, 0)

    def test_rejects_invalid_json_gate(self) -> None:
        report = {
            "SchemaVersion": "1.0",
            "EntryPoint": "Sample.csproj",
            "Projects": [{"Name": "Sample", "Path": "Sample.csproj", "Files": []}],
            "QualityGates": [
                {"Metric": "nloc", "Subject": "M", "Threshold": "10", "Actual": "2", "Passed": "yes"}
            ],
        }
        self.assertNotEqual(self.validate("json", report).returncode, 0)

    def test_valid_sarif_210(self) -> None:
        report = {
            "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "test"}}, "results": []}],
        }
        self.assertEqual(self.validate("sarif", report).returncode, 0)

    def test_rejects_unsafe_sarif_uri(self) -> None:
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "test"}},
                    "results": [
                        {
                            "ruleId": "CA0001",
                            "locations": [
                                {"physicalLocation": {"artifactLocation": {"uri": "../outside.cs"}}}
                            ],
                        }
                    ],
                }
            ],
        }
        self.assertNotEqual(self.validate("sarif", report).returncode, 0)


if __name__ == "__main__":
    unittest.main()
