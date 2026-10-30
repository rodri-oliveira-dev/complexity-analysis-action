#!/usr/bin/env python3

"""Create deterministic, non-publishing release-readiness artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


VERSION_RE = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CLI_DEFAULT_RE = re.compile(r"(?ms)^  tool-version:\s.*?^    default: ([^\s]+)$")
REQUIRED_FILES = (
    "action.yml",
    "publish-pr-report/action.yml",
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "RELEASE_CHECKLIST.md",
    "docs/maintainers.md",
    "docs/marketplace.md",
    "docs/release-readiness.md",
    "docs/releases/v1.0.0.md",
    "LICENSE",
)


class ReadinessError(RuntimeError):
    pass


def run_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git command failed"
        raise ReadinessError(detail)
    return result.stdout.strip()


def changelog_section(document: str, version: str) -> str:
    number = version.removeprefix("v")
    match = re.search(
        rf"(?ms)^## \[{re.escape(number)}\](?: - [^\n]+)?\n\n(?P<body>.*?)(?=^## \[|\Z)",
        document,
    )
    if not match or not match.group("body").strip():
        raise ReadinessError(f"CHANGELOG.md has no entry for {number}.")
    return match.group("body").strip()


def cli_default(action_document: str) -> str:
    match = CLI_DEFAULT_RE.search(action_document)
    if not match or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", match.group(1)):
        raise ReadinessError("action.yml does not contain an exact stable CLI default.")
    return match.group(1)


def require_published_cli(version: str) -> None:
    url = "https://api.nuget.org/v3-flatcontainer/complexityanalysis.tool/index.json"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise ReadinessError(f"Unable to verify ComplexityAnalysis.Tool on NuGet.org: {error}") from error
    if version not in payload.get("versions", []):
        raise ReadinessError(f"ComplexityAnalysis.Tool {version} is not published on NuGet.org.")


def file_manifest(root: Path) -> list[dict[str, str]]:
    tracked = run_git(root, "ls-files", "-z").split("\0")
    entries = []
    for relative in sorted(item for item in tracked if item):
        path = root / relative
        if not path.is_file():
            raise ReadinessError(f"Tracked release file is missing: {relative}")
        entries.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--skip-remote-check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    if not VERSION_RE.fullmatch(args.version):
        raise SystemExit("version must be a stable semantic version such as v1.0.0")
    if not SHA_RE.fullmatch(args.commit):
        raise SystemExit("commit must be a lowercase 40-character SHA")

    head = run_git(root, "rev-parse", "HEAD")
    resolved = run_git(root, "rev-parse", f"{args.commit}^{{commit}}")
    if head != args.commit or resolved != args.commit:
        raise ReadinessError("The requested commit must be the exact checked-out HEAD commit.")
    if run_git(root, "status", "--porcelain"):
        raise ReadinessError("The release checkout must be clean before artifacts are generated.")
    if run_git(root, "tag", "--list", args.version):
        raise ReadinessError(f"Tag {args.version} already exists locally.")
    if not args.skip_remote_check and run_git(root, "ls-remote", "--tags", "origin", f"refs/tags/{args.version}"):
        raise ReadinessError(f"Tag {args.version} already exists on origin.")

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            raise ReadinessError(f"Required release file is missing: {relative}")

    action_document = (root / "action.yml").read_text(encoding="utf-8")
    tool_version = cli_default(action_document)
    require_published_cli(tool_version)
    changelog_section((root / "CHANGELOG.md").read_text(encoding="utf-8"), args.version)
    notes_path = root / "docs" / "releases" / f"{args.version}.md"
    if not notes_path.is_file():
        raise ReadinessError(f"Detailed release notes are missing: {notes_path.relative_to(root)}")
    notes = notes_path.read_text(encoding="utf-8").strip()
    files = file_manifest(root)

    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schemaVersion": "complexity-action-release/1.0",
        "actionVersion": args.version,
        "commit": args.commit,
        "cli": {
            "package": "ComplexityAnalysis.Tool",
            "version": tool_version,
            "targetFramework": "net10.0",
            "runtime": "Microsoft.NETCore.App 10.0",
        },
        "supportedRunners": ["ubuntu-latest"],
        "marketplace": {
            "name": "Complexity Analysis",
            "categories": ["code-quality", "continuous-integration"],
            "published": False,
        },
        "publicationPerformed": False,
        "files": files,
    }
    (output / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    (output / "release-notes.md").write_text(
        f"{notes}\n", encoding="utf-8", newline="\n"
    )
    print(f"Prepared non-publishing release artifacts for {args.version} at {args.commit}.")


if __name__ == "__main__":
    try:
        main()
    except ReadinessError as error:
        raise SystemExit(f"release readiness failed: {error}") from error
