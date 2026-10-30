"""Tests for published release and tag verification; no GitHub requests required."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "verify_publication", Path(__file__).resolve().parents[1] / "scripts" / "verify-publication.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
REPO = "rodri-oliveira-dev/complexity-analysis-action"
BASE = f"https://api.github.com/repos/{REPO}"
COMMIT = "a" * 40
ANNOTATED = "b" * 40

def responses(major=COMMIT, draft=False):
    return {
        BASE + "/releases/tags/v1.0.0": {
            "tag_name": "v1.0.0", "draft": draft, "prerelease": False,
            "published_at": "2026-10-30T15:00:00Z", "html_url": "https://github.com/test/release"
        },
        BASE + "/git/ref/tags/v1.0.0": {"object": {"sha": ANNOTATED, "type": "tag"}},
        BASE + "/git/tags/" + ANNOTATED: {"object": {"sha": COMMIT, "type": "commit"}},
        BASE + "/git/ref/tags/v1": {"object": {"sha": major, "type": "commit"}},
    }

class PublicationVerificationTests(unittest.TestCase):
    def test_annotated_release_and_major_tag(self):
        data = responses()
        with patch.object(m, "fetch_json", side_effect=lambda url, token: data[url]):
            report = m.verify(REPO, "v1.0.0", COMMIT, "", True)
        self.assertTrue(report["stableReleaseVerified"])
        self.assertTrue(report["majorReferenceVerified"])
        self.assertEqual(report["marketplaceListing"], "manual-UI-confirmation-required")

    def test_rejects_mismatched_major(self):
        data = responses("c" * 40)
        with patch.object(m, "fetch_json", side_effect=lambda url, token: data[url]):
            with self.assertRaisesRegex(m.VerificationError, "v1 points to"):
                m.verify(REPO, "v1.0.0", COMMIT, "", True)

    def test_rejects_draft(self):
        data = responses(draft=True)
        with patch.object(m, "fetch_json", side_effect=lambda url, token: data[url]):
            with self.assertRaisesRegex(m.VerificationError, "not published"):
                m.verify(REPO, "v1.0.0", COMMIT, "", False)

    def test_rejects_invalid_identifiers_before_http(self):
        with patch.object(m, "fetch_json") as fetch:
            for repo, version, sha in [
                ("owner/repo/path", "v1.0.0", COMMIT),
                (REPO, "v1.0.0-preview", COMMIT),
                (REPO, "v1.0.0", "bad"),
            ]:
                with self.assertRaises(m.VerificationError):
                    m.verify(repo, version, sha, "", False)
            fetch.assert_not_called()

    def test_rejects_incorrect_release_sha(self):
        data = responses()
        with patch.object(m, "fetch_json", side_effect=lambda url, token: data[url]):
            with self.assertRaisesRegex(m.VerificationError, "expected"):
                m.verify(REPO, "v1.0.0", "d" * 40, "", False)

if __name__ == "__main__":
    unittest.main()
