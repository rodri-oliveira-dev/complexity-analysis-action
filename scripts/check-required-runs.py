#!/usr/bin/env python3

"""Require successful validation workflows for an exact release commit."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


REQUIRED_WORKFLOWS = ("CI", "End-to-end", "CodeQL")


def latest_by_workflow(runs: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    selected: dict[str, dict[str, object]] = {}
    for run in runs:
        name = run.get("name")
        if name not in REQUIRED_WORKFLOWS:
            continue
        current = selected.get(str(name))
        timestamp = str(run.get("run_started_at") or run.get("created_at") or "")
        current_timestamp = str((current or {}).get("run_started_at") or (current or {}).get("created_at") or "")
        if current is None or timestamp > current_timestamp:
            selected[str(name)] = run
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required to inspect workflow results")
    query = urllib.parse.urlencode({"head_sha": args.commit, "status": "completed", "per_page": 100})
    url = f"https://api.github.com/repos/{args.repository}/actions/runs?{query}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "complexity-analysis-action-release-readiness",
        "X-GitHub-Api-Version": "2026-03-10",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    selected = latest_by_workflow(payload.get("workflow_runs", []))
    checks = {
        name: {
            "conclusion": selected.get(name, {}).get("conclusion", "missing"),
            "url": selected.get(name, {}).get("html_url", ""),
        }
        for name in REQUIRED_WORKFLOWS
    }
    passed = all(item["conclusion"] == "success" for item in checks.values())
    result = {
        "commit": args.commit,
        "requiredWorkflows": checks,
        "requiredWorkflowResultsPassed": passed,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    if not passed:
        raise SystemExit("required workflow results are missing or unsuccessful")


if __name__ == "__main__":
    main()
