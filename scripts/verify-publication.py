#!/usr/bin/env python3
"""Read-only verification of a published GitHub Action release and tag targets."""
from __future__ import annotations
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
VERSION_RE = re.compile(r"^v([1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

class VerificationError(RuntimeError):
    pass

def fetch_json(url: str, token: str) -> dict:
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "complexity-action-release-verification",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
            result = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise VerificationError(f"GitHub API request failed: {url}: {exc}") from exc
    if not isinstance(result, dict):
        raise VerificationError("Unexpected GitHub API response")
    return result

def resolve_tag_commit(repo: str, tag: str, token: str) -> str:
    prefix = f"https://api.github.com/repos/{repo}"
    obj = fetch_json(f"{prefix}/git/ref/tags/{urllib.parse.quote(tag, safe='')}", token).get("object")
    seen = set()
    for _ in range(5):
        if not isinstance(obj, dict):
            raise VerificationError(f"Missing Git object for {tag}")
        sha, kind = obj.get("sha"), obj.get("type")
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            raise VerificationError(f"Invalid Git object SHA for {tag}")
        if kind == "commit":
            return sha
        if kind != "tag" or sha in seen:
            raise VerificationError(f"Invalid or cyclic annotated tag: {tag}")
        seen.add(sha)
        obj = fetch_json(f"{prefix}/git/tags/{sha}", token).get("object")
    raise VerificationError(f"Tag {tag} resolution exceeded the depth limit")

def verify(repo: str, version: str, commit: str, token: str, check_major: bool) -> dict:
    if not REPO_RE.fullmatch(repo):
        raise VerificationError("Repository must be owner/name")
    v = VERSION_RE.fullmatch(version)
    if not v:
        raise VerificationError("Version must be stable vMAJOR.MINOR.PATCH")
    if not SHA_RE.fullmatch(commit):
        raise VerificationError("Commit must be a lowercase full 40-character SHA")
    release = fetch_json(f"https://api.github.com/repos/{repo}/releases/tags/{version}", token)
    if release.get("tag_name") != version or release.get("draft") is not False or release.get("prerelease") is not False or not release.get("published_at"):
        raise VerificationError("The requested stable release is not published")
    version_commit = resolve_tag_commit(repo, version, token)
    if version_commit != commit:
        raise VerificationError(f"{version} points to {version_commit}, expected {commit}")
    major = "v" + v.group(1)
    major_commit = resolve_tag_commit(repo, major, token) if check_major else None
    if check_major and major_commit != commit:
        raise VerificationError(f"{major} points to {major_commit}, expected {commit}")
    return {"schemaVersion": "complexity-action-release-verification/1.0",
            "repository": repo, "version": version, "expectedCommit": commit,
            "releaseUrl": release.get("html_url", ""), "releaseTagCommit": version_commit,
            "majorReference": major, "majorReferenceCommit": major_commit,
            "majorReferenceVerified": check_major, "stableReleaseVerified": True,
            "marketplaceListing": "manual-UI-confirmation-required",
            "externalConsumerTest": "separate-repository-validation-required"}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--verify-major", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.repository, args.version, args.commit, os.environ.get("GITHUB_TOKEN", ""), args.verify_major)
    except VerificationError as exc:
        raise SystemExit(f"publication verification failed: {exc}") from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Verified {args.version} at {args.commit}; Marketplace visibility requires owner confirmation.")

if __name__ == "__main__":
    main()
