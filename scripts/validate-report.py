#!/usr/bin/env python3

import argparse
import json
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


def fail(message: str) -> None:
    print(f"::error title=Complexity Analysis report validation failed::{message}")
    raise SystemExit(1)


def read_json(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"{path.name} is not valid UTF-8 JSON: {error}")


def validate_json_report(document: object) -> None:
    if not isinstance(document, dict):
        fail("The JSON report root must be an object.")
    required = {
        "SchemaVersion": str,
        "EntryPoint": str,
        "Projects": list,
        "QualityGates": list,
    }
    for name, expected_type in required.items():
        if not isinstance(document.get(name), expected_type):
            fail(f"The JSON report is missing a valid '{name}' property.")
    for gate in document["QualityGates"]:
        if not isinstance(gate, dict) or not all(
            key in gate for key in ("Metric", "Subject", "Threshold", "Actual", "Passed")
        ):
            fail("The JSON report contains an invalid quality-gate result.")


def artifact_path(uri: str) -> PurePosixPath:
    parsed = urlsplit(uri)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        fail(f"SARIF artifact URI '{uri}' must be a repository-relative path.")
    decoded = unquote(parsed.path)
    path = PurePosixPath(decoded)
    if path.is_absolute() or ".." in path.parts or "\\" in decoded:
        fail(f"SARIF artifact URI '{uri}' is not a safe repository-relative path.")
    return path


def validate_sarif(document: object, workspace: Path | None, code_scanning: bool, size: int) -> None:
    if not isinstance(document, dict) or document.get("version") != "2.1.0":
        fail("The SARIF report must be a SARIF 2.1.0 object.")
    runs = document.get("runs")
    if not isinstance(runs, list) or not runs:
        fail("The SARIF report must contain at least one run.")
    for run in runs:
        if not isinstance(run, dict):
            fail("The SARIF report contains an invalid run.")
        tool = run.get("tool")
        driver = tool.get("driver") if isinstance(tool, dict) else None
        if not isinstance(driver, dict) or not driver.get("name"):
            fail("Each SARIF run must identify its tool driver.")
        results = run.get("results")
        if not isinstance(results, list):
            fail("Each SARIF run must contain a results array.")
        for result in results:
            if not isinstance(result, dict) or not result.get("ruleId"):
                fail("The SARIF report contains a result without a ruleId.")
            for location in result.get("locations", []):
                physical = location.get("physicalLocation", {})
                artifact = physical.get("artifactLocation", {})
                uri = artifact.get("uri")
                if not isinstance(uri, str) or not uri:
                    fail("A SARIF physical location is missing its artifact URI.")
                relative = artifact_path(uri)
                if code_scanning and workspace is not None and not (workspace / Path(*relative.parts)).is_file():
                    fail(
                        f"SARIF artifact URI '{uri}' does not resolve from the repository root. "
                        "Confirm that analysis ran from GITHUB_WORKSPACE and that the file is part of the checkout."
                    )
    if code_scanning and size > 10 * 1024 * 1024:
        fail("The SARIF report exceeds GitHub Code Scanning's 10 MB upload limit.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("format", choices=("json", "sarif"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--code-scanning", action="store_true")
    args = parser.parse_args()

    document = read_json(args.path)
    if args.format == "json":
        validate_json_report(document)
    else:
        workspace = args.workspace.resolve() if args.workspace else None
        validate_sarif(document, workspace, args.code_scanning, args.path.stat().st_size)


if __name__ == "__main__":
    main()
