"""Checks for consistent, immutable third-party Action pins in executable entry points."""

from collections import defaultdict
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ROOT / "action.yml",
    *(ROOT / ".github" / "workflows").glob("*.yml"),
]
PIN = re.compile(
    r"(?m)^\s*-?\s*uses:\s*"
    r"(?P<action>actions/(?:checkout|setup-dotnet)|"
    r"github/codeql-action/(?:init|analyze|upload-sarif))"
    r"@(?P<sha>[0-9a-f]{40})\s*$"
)


class DependencyPinsTests(unittest.TestCase):
    def test_runtime_references_to_each_action_use_the_same_commit(self):
        pins = defaultdict(set)
        for path in SOURCES:
            for match in PIN.finditer(path.read_text(encoding="utf-8")):
                pins[match.group("action")].add(match.group("sha"))
        self.assertIn("actions/checkout", pins)
        self.assertIn("actions/setup-dotnet", pins)
        self.assertIn("github/codeql-action/upload-sarif", pins)
        for action, shas in pins.items():
            with self.subTest(action=action):
                self.assertEqual(len(shas), 1, f"Inconsistent {action} pins: {shas}")
        codeql_pins = {
            sha for action, shas in pins.items()
            if action.startswith("github/codeql-action/")
            for sha in shas
        }
        self.assertEqual(len(codeql_pins), 1, "All CodeQL components should use the same release")


if __name__ == "__main__":
    unittest.main()
