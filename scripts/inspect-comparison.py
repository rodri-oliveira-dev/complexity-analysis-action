#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def fail(message: str) -> None:
    print(f"::error title=Complexity comparison report validation failed::{message}")
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        with args.path.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"comparison.json is not valid UTF-8 JSON: {error}")

    if not isinstance(document, dict) or document.get("SchemaVersion") != "complexity-comparison/1.0":
        fail("The comparison report does not use schema complexity-comparison/1.0.")
    for name in ("BaselineSchemaVersion", "CurrentSchemaVersion"):
        if not isinstance(document.get(name), str) or not document[name]:
            fail(f"The comparison report is missing a valid '{name}'.")
    findings = document.get("Findings")
    if not isinstance(findings, list):
        fail("The comparison report is missing its Findings array.")

    regressions = 0
    for finding in findings:
        if not isinstance(finding, dict):
            fail("The comparison report contains an invalid finding.")
        if not isinstance(finding.get("StableId"), str) or not finding["StableId"]:
            fail("A comparison finding is missing StableId.")
        classification = finding.get("Classification")
        if not isinstance(classification, str) or not classification:
            fail("A comparison finding is missing Classification.")
        if classification == "regression":
            regressions += 1

    print(regressions)


if __name__ == "__main__":
    main()
