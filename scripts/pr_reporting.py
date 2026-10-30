#!/usr/bin/env python3

"""Validated PR reporting model and deterministic Markdown renderer."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "complexity-pr-report/1.0"
MARKER = "<!-- complexity-analysis-action:pr-report:v1 -->"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CLASSIFICATIONS = {
    "regression", "improvement", "equivalent", "incomparable",
    "ambiguous", "added", "removed",
}
MAX_REPORT_BYTES = 10 * 1024 * 1024
MAX_FINDINGS = 200_000
MAX_COMMENT_FINDINGS = 10
MAX_COMMENT_LENGTH = 60_000


class ReportError(ValueError):
    pass


def load_json(path: Path, maximum: int = MAX_REPORT_BYTES) -> Any:
    try:
        size = path.stat().st_size
        if size > maximum:
            raise ReportError(f"Report exceeds the {maximum}-byte limit.")
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except ReportError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReportError(f"Report is not valid UTF-8 JSON: {error}") from error


def text(value: Any, name: str, maximum: int = 4096, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not allow_empty) or len(value) > maximum:
        raise ReportError(f"{name} is not a valid string.")
    if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
        raise ReportError(f"{name} contains control characters.")
    return value


def safe_markdown(value: Any, maximum: int = 4096) -> str:
    rendered = str(value)[:maximum]
    rendered = html.escape(rendered, quote=False)
    return rendered.replace("|", "&#124;").replace("`", "&#96;").replace("\r", " ").replace("\n", " ")


def validate_comparison(document: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not isinstance(document, dict) or document.get("SchemaVersion") != "complexity-comparison/1.0":
        raise ReportError("Comparison schema must be complexity-comparison/1.0.")
    for key in ("BaselineSchemaVersion", "CurrentSchemaVersion"):
        text(document.get(key), key, 128)
    findings = document.get("Findings")
    if not isinstance(findings, list) or len(findings) > MAX_FINDINGS:
        raise ReportError("Findings is missing or exceeds the safety limit.")

    counts = {name: 0 for name in CLASSIFICATIONS}
    validated: list[dict[str, Any]] = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ReportError(f"Finding {index} is not an object.")
        stable_id = text(finding.get("StableId"), f"Findings[{index}].StableId")
        classification = text(finding.get("Classification"), f"Findings[{index}].Classification", 32)
        if classification not in CLASSIFICATIONS:
            raise ReportError(f"Finding {index} has an unsupported classification.")
        reason = text(finding.get("Reason"), f"Findings[{index}].Reason", allow_empty=True)
        location = finding.get("Location")
        evidence = finding.get("Evidence")
        before = finding.get("Before")
        after = finding.get("After")
        if before is not None:
            before = text(before, f"Findings[{index}].Before", 256)
        if after is not None:
            after = text(after, f"Findings[{index}].After", 256)
        file_path = ""
        start_line = 0
        if location is not None:
            if not isinstance(location, dict):
                raise ReportError(f"Finding {index} has an invalid location.")
            file_path = text(location.get("FilePath"), f"Findings[{index}].Location.FilePath")
            start_line = location.get("StartLine", 0)
            if not isinstance(start_line, int) or isinstance(start_line, bool) or start_line < 0:
                raise ReportError(f"Finding {index} has an invalid start line.")
        if evidence is not None and not isinstance(evidence, dict):
            raise ReportError(f"Finding {index} has invalid evidence.")
        if classification == "regression" and (
            before is None or after is None or not reason or not file_path or evidence is None
        ):
            raise ReportError(
                f"Finding {index} claims a regression without before/after values, location, reason, and evidence."
            )
        counts[classification] += 1
        validated.append({
            "StableId": stable_id,
            "Classification": classification,
            "Reason": reason,
            "Before": before,
            "After": after,
            "FilePath": file_path,
            "StartLine": start_line,
            "Evidence": evidence,
        })
    return validated, counts


def validate_envelope(document: Any, *, repository: str | None = None,
                      head_sha: str | None = None, pr_number: int | None = None,
                      run_id: str | None = None, workflow_name: str | None = None,
                      base_sha: str | None = None) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("SchemaVersion") != SCHEMA:
        raise ReportError(f"Report schema must be {SCHEMA}.")
    repo = text(document.get("Repository"), "Repository", 256)
    if not REPOSITORY_RE.fullmatch(repo):
        raise ReportError("Repository is invalid.")
    pull = document.get("PullRequest")
    if not isinstance(pull, dict):
        raise ReportError("PullRequest metadata is missing.")
    number = pull.get("Number")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise ReportError("Pull request number is invalid.")
    report_base_sha = text(pull.get("BaseSha"), "BaseSha", 40)
    report_head = text(pull.get("HeadSha"), "HeadSha", 40)
    if not SHA_RE.fullmatch(report_base_sha) or not SHA_RE.fullmatch(report_head):
        raise ReportError("Pull request revisions must be lowercase 40-character SHAs.")
    head_repository = text(pull.get("HeadRepository"), "HeadRepository", 256)
    is_fork = pull.get("IsFork")
    if not REPOSITORY_RE.fullmatch(head_repository) or not isinstance(is_fork, bool):
        raise ReportError("Pull request head repository metadata is invalid.")
    if is_fork != (head_repository.lower() != repo.lower()):
        raise ReportError("Pull request fork metadata is inconsistent.")
    solution = text(document.get("Solution"), "Solution")
    if solution.startswith("/") or ".." in Path(solution).parts:
        raise ReportError("Solution must be a repository-relative path.")
    comparison = document.get("Comparison")
    if not isinstance(comparison, dict):
        raise ReportError("Comparison summary is missing.")
    status = text(comparison.get("Status"), "Comparison.Status", 64)
    if status not in {"no-regressions", "regressions-detected"}:
        raise ReportError("Only completed comparisons can be published.")
    comparison_base = comparison.get("Base")
    if not isinstance(comparison_base, dict):
        raise ReportError("Comparison base metadata is missing.")
    base_kind = text(comparison_base.get("Kind"), "Comparison.Base.Kind", 32)
    comparison_base_sha = comparison_base.get("Sha")
    if base_kind == "commit":
        if not isinstance(comparison_base_sha, str) or not SHA_RE.fullmatch(comparison_base_sha):
            raise ReportError("Comparison commit baseline is invalid.")
    elif base_kind == "snapshot":
        if comparison_base_sha is not None:
            raise ReportError("A supplied baseline snapshot must not claim a commit SHA.")
    else:
        raise ReportError("Comparison base kind is invalid.")
    findings = comparison.get("Regressions")
    if not isinstance(findings, list) or len(findings) > MAX_FINDINGS:
        raise ReportError("Regression details are invalid.")
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict) or finding.get("Classification") != "regression":
            raise ReportError(f"Regression {index} is invalid.")
        for key in ("StableId", "Reason", "Before", "After", "FilePath"):
            text(finding.get(key), f"Regressions[{index}].{key}")
        start_line = finding.get("StartLine")
        if not isinstance(start_line, int) or isinstance(start_line, bool) or start_line < 0:
            raise ReportError(f"Regression {index} has an invalid start line.")
        if not isinstance(finding.get("Evidence"), dict):
            raise ReportError(f"Regression {index} has no validated evidence.")
    counts = comparison.get("Counts")
    if not isinstance(counts, dict):
        raise ReportError("Comparison counts are missing.")
    for key in ("Regressions", "Improvements", "Unchanged", "Incomparable"):
        value = counts.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ReportError(f"Count {key} is invalid.")
    if counts["Regressions"] != len(findings):
        raise ReportError("Regression count does not match the details.")
    if (status == "regressions-detected") != bool(findings):
        raise ReportError("Comparison status does not match the regression count.")
    quality = text(document.get("QualityGateStatus"), "QualityGateStatus", 64)
    if quality not in {"not-configured", "passed", "failed", "unknown"}:
        raise ReportError("Quality-gate status is invalid.")
    provenance = document.get("Provenance")
    if not isinstance(provenance, dict):
        raise ReportError("Provenance is missing.")
    report_run_id = text(provenance.get("WorkflowRunId"), "WorkflowRunId", 32)
    report_workflow = text(provenance.get("WorkflowName"), "WorkflowName", 256)
    if not report_run_id.isdigit():
        raise ReportError("Workflow run ID is invalid.")
    artifacts = document.get("Artifacts")
    if not isinstance(artifacts, list) or len(artifacts) > 20:
        raise ReportError("Artifact references are invalid.")
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict) or not isinstance(artifact.get("Available"), bool):
            raise ReportError(f"Artifact {index} is invalid.")
        text(artifact.get("Name"), f"Artifacts[{index}].Name", 128)
        artifact_path = text(artifact.get("Path"), f"Artifacts[{index}].Path", allow_empty=True)
        if artifact_path and (artifact_path.startswith("/") or ".." in Path(artifact_path).parts):
            raise ReportError(f"Artifact {index} path is not repository-relative.")
    expected_run_url = f"https://github.com/{repo}/actions/runs/{report_run_id}"
    if document.get("RunUrl") != expected_run_url:
        raise ReportError("Workflow run URL is invalid.")
    if repository is not None and repo.lower() != repository.lower():
        raise ReportError("Artifact repository does not match the trusted workflow context.")
    if head_sha is not None and report_head != head_sha.lower():
        raise ReportError("Artifact head SHA does not match the trusted workflow context.")
    if base_sha is not None and base_sha.lower() != report_base_sha:
        raise ReportError("Artifact event base SHA does not match the trusted workflow context.")
    if pr_number is not None and number != pr_number:
        raise ReportError("Artifact PR number does not match the trusted workflow context.")
    if run_id is not None and report_run_id != run_id:
        raise ReportError("Artifact run ID does not match the trusted workflow context.")
    if workflow_name is not None and report_workflow != workflow_name:
        raise ReportError("Artifact workflow identity does not match the trusted workflow context.")
    return document


def render_comment(report: dict[str, Any], limit: int = MAX_COMMENT_FINDINGS) -> str:
    pull = report["PullRequest"]
    comparison = report["Comparison"]
    counts = comparison["Counts"]
    regressions = comparison["Regressions"]
    base = comparison["Base"]
    base_display = base["Sha"][:12] if base["Kind"] == "commit" else "Provided snapshot"
    overall = "Regressions detected" if regressions else "No proven regressions"
    lines = [
        MARKER,
        "## Complexity analysis",
        "",
        f"**{overall}.** Analysis completed for `{safe_markdown(report['Solution'])}`.",
        "",
        "| Item | Result |",
        "| --- | --- |",
        f"| Repository | `{safe_markdown(report['Repository'])}` |",
        f"| Comparison base | `{safe_markdown(base_display)}` |",
        f"| Head | `{safe_markdown(pull['HeadSha'][:12])}` |",
        f"| Comparison | {safe_markdown(comparison['Status'])} |",
        "| Execution errors | None (comparison completed) |",
        f"| Proven regressions | {counts['Regressions']} |",
        f"| Improvements | {counts['Improvements']} |",
        f"| Unchanged | {counts['Unchanged']} |",
        f"| Incomparable | {counts['Incomparable']} |",
        f"| Quality gates | {safe_markdown(report['QualityGateStatus'])} |",
        "",
    ]
    if regressions:
        shown = regressions[:limit]
        lines.extend((f"<details{' open' if len(regressions) <= 3 else ''}>",
                      f"<summary>Regression details ({len(shown)} of {len(regressions)})</summary>", ""))
        for finding in shown:
            location = safe_markdown(finding["FilePath"])
            if finding.get("StartLine"):
                location += f":{finding['StartLine']}"
            evidence = json.dumps(finding["Evidence"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            lines.extend((
                f"### `{safe_markdown(finding['StableId'])}`",
                "",
                f"- File: `{location}`",
                f"- Complexity: `{safe_markdown(finding['Before'])}` → `{safe_markdown(finding['After'])}`",
                f"- Classification: `{safe_markdown(finding['Classification'])}`",
                f"- Evidence: {safe_markdown(finding['Reason'])}",
                f"- CLI evidence: <code>{safe_markdown(evidence, 1500)}</code>",
                "",
            ))
        if len(regressions) > limit:
            lines.append(f"{len(regressions) - limit} additional regressions are available in the comparison artifact.\n")
        lines.extend(("</details>", ""))
    else:
        lines.extend(("No finding with complete CLI regression evidence was reported.", ""))
    artifacts = report.get("Artifacts", [])
    if artifacts:
        lines.extend(("### Reports", ""))
        for artifact in artifacts:
            if isinstance(artifact, dict) and artifact.get("Available") is True:
                lines.append(f"- {safe_markdown(artifact.get('Name', 'Report'))}: `{safe_markdown(artifact.get('Path', ''))}`")
        run_url = report.get("RunUrl")
        if isinstance(run_url, str) and run_url.startswith("https://github.com/"):
            lines.append(f"- [Workflow run]({run_url})")
    lines.extend(("", "_Generated from the validated CLI comparison report. This comment is updated on repeated runs._"))
    body = "\n".join(lines)
    if len(body) > MAX_COMMENT_LENGTH:
        raise ReportError("Rendered comment exceeds GitHub's safe comment size.")
    return body
