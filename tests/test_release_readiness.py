import importlib.util
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "prepare_release", Path(__file__).resolve().parents[1] / "scripts" / "prepare-release.py"
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class ReleaseReadinessTests(unittest.TestCase):
    def test_workflow_uses_main_dispatch_sha_consistently(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github" / "workflows" / "release-readiness.yml"
        ).read_text(encoding="utf-8")
        workflow_inputs = workflow.split("    inputs:\n", 1)[1].split("\npermissions:", 1)[0]

        self.assertNotRegex(workflow_inputs, r"(?m)^\s+commit:")
        self.assertIn('RELEASE_REF: ${{ github.ref }}', workflow)
        self.assertIn('RELEASE_COMMIT: ${{ github.sha }}', workflow)
        self.assertIn('[[ "$RELEASE_REF" != "refs/heads/main" ]]', workflow)
        self.assertIn('ref: ${{ github.sha }}', workflow)
        self.assertIn('--commit "$RELEASE_COMMIT"', workflow)
        self.assertNotIn("inputs.commit", workflow)
        self.assertIn('RELEASE_VERSION: ${{ inputs.version }}', workflow)
        preflight = workflow.split("      - name: Require release readiness from main\n", 1)[1].split(
            "      # actions/checkout", 1
        )[0]
        self.assertIn('RELEASE_VERSION: ${{ inputs.version }}', preflight)
        preflight_script = preflight.split("        run: |\n", 1)[1]
        self.assertIn('echo "Preparing $RELEASE_VERSION from main commit $RELEASE_COMMIT"', preflight_script)
        self.assertNotIn("${{ inputs.version }}", preflight_script)

    def test_accepts_stable_action_version(self):
        self.assertIsNotNone(module.VERSION_RE.fullmatch("v1.0.0"))
        self.assertIsNone(module.VERSION_RE.fullmatch("1.0.0"))
        self.assertIsNone(module.VERSION_RE.fullmatch("v1.0.0-beta.1"))

    def test_reads_exact_cli_default(self):
        document = "inputs:\n  tool-version:\n    description: exact\n    default: 1.0.1\n"
        self.assertEqual(module.cli_default(document), "1.0.1")
        with self.assertRaises(module.ReadinessError):
            module.cli_default(document.replace("1.0.1", "1.*"))

    def test_extracts_matching_changelog_entry(self):
        document = "# Log\n\n## [1.0.0] - Unreleased\n\nReady.\n\n## [0.9.0]\n\nOld.\n"
        self.assertEqual(module.changelog_section(document, "v1.0.0"), "Ready.")
        with self.assertRaises(module.ReadinessError):
            module.changelog_section(document, "v2.0.0")


if __name__ == "__main__":
    unittest.main()
