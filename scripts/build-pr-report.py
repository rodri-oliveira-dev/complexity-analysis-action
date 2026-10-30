#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path

from pr_reporting import ReportError, SCHEMA, load_json, validate_comparison, validate_envelope


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ReportError(f"{name} is required.")
    return value


def relative_artifact(name: str, env_name: str, workspace: Path) -> dict[str, object]:
    value = os.environ.get(env_name, "")
    if not value:
        return {"Name": name, "Path": "", "Available": False}
    path = Path(value)
    try:
        display = path.resolve().relative_to(workspace.resolve()).as_posix()
        available = path.is_file()
    except (OSError, ValueError):
        display = "unavailable"
        available = False
    return {"Name": name, "Path": display, "Available": available}


def main() -> None:
    try:
        event = load_json(Path(required("GITHUB_EVENT_PATH")), maximum=1024 * 1024)
        if not isinstance(event, dict) or not isinstance(event.get("pull_request"), dict):
            raise ReportError("A pull_request event payload is required.")
        pull = event["pull_request"]
        repository = required("GITHUB_REPOSITORY")
        if pull.get("base", {}).get("repo", {}).get("full_name") != repository:
            raise ReportError("Event repository does not match GITHUB_REPOSITORY.")
        number = pull.get("number")
        base_sha = pull.get("base", {}).get("sha")
        head_sha = pull.get("head", {}).get("sha")
        if not isinstance(number, int) or number < 1:
            raise ReportError("Event PR number is invalid.")
        for label, value in (("base", base_sha), ("head", head_sha)):
            if not isinstance(value, str) or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
                raise ReportError(f"Event {label} SHA is invalid.")
        findings, raw_counts = validate_comparison(load_json(Path(required("COMPARISON_REPORT_PATH"))))
        regressions = [finding for finding in findings if finding["Classification"] == "regression"]
        expected_count = int(required("REGRESSION_COUNT"))
        if expected_count != len(regressions):
            raise ReportError("Action output and validated comparison regression counts differ.")
        status = required("COMPARISON_STATUS")
        if status not in {"no-regressions", "regressions-detected"}:
            raise ReportError("The comparison did not complete and cannot be published as findings.")
        workspace = Path(required("WORKSPACE"))
        run_id = required("GITHUB_RUN_ID")
        if not run_id.isdigit():
            raise ReportError("GITHUB_RUN_ID is invalid.")
        base_revision_kind = required("BASE_REVISION_KIND")
        base_revision = os.environ.get("BASE_REVISION", "")
        if base_revision_kind == "commit":
            if len(base_revision) != 40 or any(c not in "0123456789abcdef" for c in base_revision):
                raise ReportError("Resolved comparison base revision is invalid.")
        elif base_revision_kind == "snapshot":
            if base_revision:
                raise ReportError("A supplied baseline snapshot must not claim a commit revision.")
        else:
            raise ReportError("Comparison base revision kind is invalid.")
        report = {
            "SchemaVersion": SCHEMA,
            "Repository": repository,
            "Solution": required("ANALYSIS_RELATIVE_PATH"),
            "PullRequest": {
                "Number": number,
                "BaseSha": base_sha,
                "HeadSha": head_sha,
                "HeadRepository": pull.get("head", {}).get("repo", {}).get("full_name", ""),
                "IsFork": pull.get("head", {}).get("repo", {}).get("full_name") != repository,
            },
            "Comparison": {
                "Status": status,
                "Base": {"Kind": base_revision_kind, "Sha": base_revision or None},
                "Counts": {
                    "Regressions": raw_counts["regression"],
                    "Improvements": raw_counts["improvement"],
                    "Unchanged": raw_counts["equivalent"],
                    "Incomparable": raw_counts["incomparable"] + raw_counts["ambiguous"],
                },
                "Regressions": regressions,
            },
            "QualityGateStatus": required("QUALITY_GATE_STATUS"),
            "Artifacts": [
                relative_artifact("Analysis JSON", "REPORT_PATH", workspace),
                relative_artifact("Analysis SARIF", "SARIF_PATH", workspace),
                relative_artifact("Baseline snapshot", "BASELINE_REPORT_PATH", workspace),
                relative_artifact("Current snapshot", "CURRENT_REPORT_PATH", workspace),
                relative_artifact("Comparison JSON", "COMPARISON_REPORT_PATH", workspace),
            ],
            "Provenance": {
                "WorkflowRunId": run_id,
                "WorkflowName": required("GITHUB_WORKFLOW"),
                "EventName": required("GITHUB_EVENT_NAME"),
            },
            "RunUrl": f"https://github.com/{repository}/actions/runs/{run_id}",
        }
        validate_envelope(
            report,
            repository=repository,
            head_sha=head_sha,
            pr_number=number,
            run_id=run_id,
            workflow_name=required("GITHUB_WORKFLOW"),
            base_sha=base_sha,
        )
        destination = Path(required("PR_REPORT_PATH"))
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ReportError, OSError, ValueError) as error:
        print(f"::error title=PR report generation failed::{error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
