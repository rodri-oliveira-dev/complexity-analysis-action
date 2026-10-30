#!/usr/bin/env python3

import json
import os
from html import escape
from pathlib import Path


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def cell(value: object) -> str:
    sanitized = escape(str(value), quote=False).replace("`", "&#96;")
    return (
        sanitized.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def display_path(value: str) -> str:
    if not value:
        return "Unavailable"
    path = Path(value)
    workspace = Path(env("WORKSPACE", "."))
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return str(path)


def overall_status() -> str:
    code = env("ANALYSIS_EXIT_CODE")
    if code == "130":
        return "Canceled"
    if code not in ("0", "2"):
        return "Failed: analysis or configuration error"
    if env("UPLOAD_SARIF") == "true" and env("SARIF_VALIDATION_OUTCOME") != "success":
        return "Failed: SARIF did not pass Code Scanning validation"
    if env("UPLOAD_SARIF") == "true" and env("UPLOAD_OUTCOME") == "failure":
        return "Failed: SARIF upload was rejected"
    if env("COMPARISON_STATUS") in ("unavailable", "failed"):
        return "Failed: requested comparison unavailable"
    if env("COMPARISON_STATUS") == "regressions-detected" and env("FAIL_ON_REGRESSION") == "true":
        return "Failed: complexity regression"
    if code == "0":
        return "Succeeded"
    if code == "2":
        if env("FAIL_ON_QUALITY_GATE") == "true":
            return "Failed: quality gate"
        return "Succeeded with quality-gate violations allowed"
    return "Failed: quality gate"


def threshold_rows() -> list[tuple[str, str]]:
    definitions = (
        ("Maximum Big-O", "MAX_COMPLEXITY"),
        ("Maximum cyclomatic complexity", "MAX_CYCLOMATIC_COMPLEXITY"),
        ("Maximum cognitive complexity", "MAX_COGNITIVE_COMPLEXITY"),
        ("Maximum nesting depth", "MAX_NESTING_DEPTH"),
        ("Maximum method NLOC", "MAX_METHOD_NLOC"),
        ("Maximum duplicate rate", "MAX_DUPLICATE_RATE"),
    )
    return [(label, env(name)) for label, name in definitions if env(name)]


def quality_gates(report_path: str) -> list[dict[str, object]]:
    try:
        with Path(report_path).open("r", encoding="utf-8") as stream:
            report = json.load(stream)
        gates = report.get("QualityGates", [])
        return gates if isinstance(gates, list) else []
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []


def main() -> None:
    summary_path = env("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    thresholds = threshold_rows()
    gates = quality_gates(env("REPORT_PATH"))
    failed = sum(1 for gate in gates if gate.get("Passed") is False)
    passed = sum(1 for gate in gates if gate.get("Passed") is True)

    lines = [
        "# Complexity Analysis",
        "",
        "| Item | Result |",
        "| --- | --- |",
        f"| Analyzed entry point | `{cell(display_path(env('ANALYSIS_PATH')))}` |",
        f"| CLI version | `{cell(env('TOOL_VERSION', 'unknown'))}` |",
        f"| Analysis status | {cell(env('ANALYSIS_STATUS', 'unknown'))} |",
        f"| Quality-gate status | {cell(env('QUALITY_GATE_STATUS', 'unknown'))} |",
        f"| Comparison status | {cell(env('COMPARISON_STATUS', 'not-requested'))} |",
        f"| Proven regressions | {cell(env('REGRESSION_COUNT', '0'))} |",
        f"| Overall execution | {cell(overall_status())} |",
        "",
        "## Configured thresholds",
        "",
    ]
    if thresholds:
        lines.extend(("| Metric | Maximum |", "| --- | --- |"))
        lines.extend(f"| {cell(label)} | `{cell(value)}` |" for label, value in thresholds)
    else:
        lines.append("No quality-gate thresholds were configured.")

    lines.extend(("", "## Quality-gate results", ""))
    if gates:
        lines.append(f"Evaluated: **{len(gates)}** · Passed: **{passed}** · Failed: **{failed}**")
        lines.extend(("", "| Result | Metric | Subject | Actual | Maximum |", "| --- | --- | --- | ---: | ---: |"))
        ordered = sorted(
            gates,
            key=lambda gate: (
                gate.get("Passed") is not False,
                str(gate.get("Metric", "")),
                str(gate.get("Subject", "")),
            ),
        )
        for gate in ordered[:50]:
            result = "PASS" if gate.get("Passed") is True else "FAIL"
            lines.append(
                f"| {result} | {cell(gate.get('Metric', ''))} | {cell(gate.get('Subject', ''))} | "
                f"{cell(gate.get('Actual', ''))} | {cell(gate.get('Threshold', ''))} |"
            )
        if len(ordered) > 50:
            lines.extend(("", f"Showing 50 of {len(ordered)} results. See the JSON report for the complete list."))
    elif thresholds and env("ANALYSIS_STATUS") == "success":
        lines.append("The CLI reported no evaluable quality-gate results and no violations.")
    else:
        lines.append("No quality-gate results are available.")

    upload_status = env("UPLOAD_OUTCOME", "not requested") if env("UPLOAD_SARIF") == "true" else "not requested"
    lines.extend(
        (
            "",
            "## Reports",
            "",
            f"- JSON: `{cell(display_path(env('REPORT_PATH')))}`",
            f"- SARIF 2.1.0: `{cell(display_path(env('SARIF_PATH')))}`",
            f"- Code Scanning upload: {cell(upload_status)}",
            f"- Baseline snapshot: `{cell(display_path(env('BASELINE_REPORT_PATH')))}`",
            f"- Current snapshot: `{cell(display_path(env('CURRENT_REPORT_PATH')))}`",
            f"- Comparison JSON: `{cell(display_path(env('COMPARISON_REPORT_PATH')))}`",
            "",
        )
    )

    with Path(summary_path).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines))


if __name__ == "__main__":
    main()
