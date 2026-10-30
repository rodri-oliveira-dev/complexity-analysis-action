#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from pr_reporting import MARKER, ReportError, load_json, render_comment, validate_envelope


class GitHubClient:
    def __init__(self, token: str, api_url: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "complexity-analysis-action",
        }

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.api_url + path, data=data, method=method, headers=self.headers)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            request_id = error.headers.get("x-github-request-id", "unavailable")
            raise ReportError(f"GitHub API returned HTTP {error.code} (request {request_id}).") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ReportError(f"GitHub API request failed: {type(error).__name__}.") from error


def publish(client: GitHubClient, report: dict[str, Any]) -> str:
    repository = report["Repository"]
    number = report["PullRequest"]["Number"]
    body = render_comment(report)
    encoded_repository = "/".join(urllib.parse.quote(part, safe="") for part in repository.split("/"))
    pull = client.request("GET", f"/repos/{encoded_repository}/pulls/{number}")
    if not isinstance(pull, dict) or pull.get("state") != "open":
        raise ReportError("The pull request is no longer open.")
    head = pull.get("head")
    if not isinstance(head, dict) or str(head.get("sha", "")).lower() != report["PullRequest"]["HeadSha"]:
        raise ReportError("The pull request head changed after this report was generated.")
    comments: list[dict[str, Any]] = []
    page = 1
    while True:
        page_comments = client.request(
            "GET", f"/repos/{encoded_repository}/issues/{number}/comments?per_page=100&page={page}"
        )
        if not isinstance(page_comments, list):
            raise ReportError("GitHub returned an invalid comment list.")
        comments.extend(page_comments)
        if len(page_comments) < 100:
            break
        page += 1
    owned = [
        comment for comment in comments
        if isinstance(comment, dict)
        and MARKER in str(comment.get("body", ""))
        and isinstance(comment.get("user"), dict)
        and comment["user"].get("login") == "github-actions[bot]"
        and comment["user"].get("type") == "Bot"
        and isinstance(comment.get("id"), int)
    ]
    if owned:
        selected = min(owned, key=lambda comment: comment["id"])
        client.request("PATCH", f"/repos/{encoded_repository}/issues/comments/{selected['id']}", {"body": body})
        return "updated"
    client.request("POST", f"/repos/{encoded_repository}/issues/{number}/comments", {"body": body})
    return "created"


def main() -> None:
    try:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise ReportError("GITHUB_TOKEN is unavailable; grant pull-requests: write only to the publishing job.")
        expected_repository = os.environ.get("EXPECTED_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY")
        expected_head = os.environ.get("EXPECTED_HEAD_SHA")
        expected_base = os.environ.get("EXPECTED_BASE_SHA")
        expected_number_raw = os.environ.get("EXPECTED_PR_NUMBER")
        expected_run = os.environ.get("EXPECTED_RUN_ID")
        expected_workflow = os.environ.get("EXPECTED_WORKFLOW_NAME")
        if (not expected_repository or not expected_head or not expected_base
                or not expected_number_raw or not expected_number_raw.isdigit()):
            raise ReportError("Trusted repository, base/head SHAs, and PR number metadata are required.")
        report = validate_envelope(
            load_json(Path(os.environ["PR_REPORT_PATH"])),
            repository=expected_repository,
            head_sha=expected_head,
            pr_number=int(expected_number_raw),
            run_id=expected_run or None,
            workflow_name=expected_workflow or None,
            base_sha=expected_base,
        )
        result = publish(GitHubClient(token, os.environ.get("GITHUB_API_URL", "https://api.github.com")), report)
        print(f"PR complexity report {result}.")
    except (KeyError, ReportError, OSError) as error:
        print(f"::warning title=PR comment publication unavailable::{error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
