#!/usr/bin/env python3

"""Report external repository settings required before release publication."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def request(repository: str, path: str, token: str) -> tuple[int, object | None]:
    url = f"https://api.github.com/repos/{repository}/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "complexity-analysis-action-release-readiness",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--default-branch", default="main")
    parser.add_argument("--immutable-releases-confirmed", choices=("true", "false"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required to inspect repository settings")

    rules_status, rules = request(args.repository, f"rules/branches/{args.default_branch}", token)
    rule_types = {
        rule.get("type") for rule in rules
        if isinstance(rules, list) and isinstance(rule, dict)
    }
    result = {
        "immutableReleasesMaintainerConfirmed": args.immutable_releases_confirmed == "true",
        "defaultBranchProtected": rules_status == 200
        and "pull_request" in rule_types
        and "required_status_checks" in rule_types,
        "defaultBranchRuleTypes": sorted(item for item in rule_types if isinstance(item, str)),
        "defaultWorkflowPermissionsExpected": "read",
        "publicationPrerequisitesSatisfied": False,
    }
    result["publicationPrerequisitesSatisfied"] = (
        result["immutableReleasesMaintainerConfirmed"] and result["defaultBranchProtected"]
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    if not result["publicationPrerequisitesSatisfied"]:
        raise SystemExit("repository release prerequisites are not satisfied")


if __name__ == "__main__":
    main()
