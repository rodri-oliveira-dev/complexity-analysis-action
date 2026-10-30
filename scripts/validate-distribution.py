#!/usr/bin/env python3

"""Validate Marketplace metadata, public examples, and documentation links."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ACTION_NAME = "Complexity Analysis"
DESCRIPTION = (
    "Analyze C# complexity with quality gates, JSON/SARIF reports, "
    "and proven regression detection."
)
CATEGORY_NAMES = {"code quality", "continuous integration"}
ALLOWED_COLORS = {"white", "black", "yellow", "blue", "green", "orange", "red", "purple", "gray-dark"}
REQUIRED_EXAMPLES = {
    "basic-analysis.yml",
    "quality-gates.yml",
    "non-blocking-analysis.yml",
    "sarif-upload.yml",
    "secure-pr-analysis.yml",
    "secure-pr-publish.yml",
    "consumer-workflow.yml",
}
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PUBLISHED_RELEASE_SHA = "2d807ef29ca03c685d224543a135d8c30dfe2c67"
ACTION_REF_PREFIX = "rodri-oliveira-dev/complexity-analysis-action@"


class DistributionError(RuntimeError):
    pass


def top_scalar(document: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(.+?)\s*$", document)
    if not match:
        raise DistributionError(f"action.yml is missing {name} metadata")
    return match.group(1).strip('"\'')


def section_keys(document: str, section: str) -> set[str]:
    lines = document.splitlines()
    collecting = False
    keys: set[str] = set()
    for line in lines:
        if line == f"{section}:":
            collecting = True
            continue
        if collecting and line and not line.startswith(" "):
            break
        if collecting:
            match = re.match(r"^  ([a-z][a-z0-9-]*):\s*$", line)
            if match:
                keys.add(match.group(1))
    return keys


def example_inputs(path: Path) -> set[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    keys: set[str] = set()
    action_indent = -1
    with_indent = -1
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if "uses: rodri-oliveira-dev/complexity-analysis-action@" in stripped:
            action_indent = indent
            with_indent = -1
            continue
        if action_indent >= 0 and indent <= action_indent and stripped.startswith("-"):
            action_indent = -1
            with_indent = -1
        if action_indent >= 0 and stripped == "with:":
            with_indent = indent
            continue
        if with_indent >= 0 and indent > with_indent:
            match = re.match(r"^([a-z][a-z0-9-]*):", stripped)
            if match:
                keys.add(match.group(1))
        elif with_indent >= 0 and stripped:
            with_indent = -1
    return keys


def validate_links(root: Path) -> int:
    checked = 0
    documents = [root / "README.md", *(root / "docs").rglob("*.md")]
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            target = target.strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative = target.split("#", 1)[0]
            if relative and not (document.parent / relative).resolve().exists():
                raise DistributionError(f"broken local documentation link in {document.relative_to(root)}: {target}")
            checked += 1
    return checked


def validate(root: Path) -> dict[str, object]:
    root_metadata = [path for name in ("action.yml", "action.yaml") if (path := root / name).is_file()]
    if len(root_metadata) != 1:
        raise DistributionError("repository must contain exactly one root action.yml or action.yaml")
    action_path = root_metadata[0]
    document = action_path.read_text(encoding="utf-8")
    action_name = top_scalar(document, "name")
    description = top_scalar(document, "description")
    author = top_scalar(document, "author")
    if action_name != ACTION_NAME or action_name.lower() in CATEGORY_NAMES:
        raise DistributionError("Marketplace action name is invalid or conflicts with a category")
    if description != DESCRIPTION or not 20 <= len(description) <= 125:
        raise DistributionError("Marketplace description is inaccurate or outside the concise length limit")
    if not author or len(author) > 100:
        raise DistributionError("Marketplace author metadata is invalid")
    icon_match = re.search(r"(?m)^  icon:\s*([a-z0-9-]+)\s*$", document)
    color_match = re.search(r"(?m)^  color:\s*([a-z-]+)\s*$", document)
    if not icon_match or icon_match.group(1) != "activity":
        raise DistributionError("branding icon must be the supported Feather activity icon")
    if not color_match or color_match.group(1) not in ALLOWED_COLORS:
        raise DistributionError("branding color is unsupported")

    required_files = ("README.md", "LICENSE", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md")
    for relative in required_files:
        if not (root / relative).is_file():
            raise DistributionError(f"required public file is missing: {relative}")

    inputs = section_keys(document, "inputs")
    outputs = section_keys(document, "outputs")
    for example_name in REQUIRED_EXAMPLES:
        path = root / "examples" / example_name
        if not path.is_file():
            raise DistributionError(f"required public example is missing: examples/{example_name}")
        unknown = example_inputs(path) - inputs
        if unknown:
            raise DistributionError(f"{path.name} uses unknown Action inputs: {sorted(unknown)}")
        example = path.read_text(encoding="utf-8")
        # Full-SHA pins also cover the publication-only nested companion Action.
        expected = ACTION_REF_PREFIX if example_name != "secure-pr-publish.yml" else (
            "rodri-oliveira-dev/complexity-analysis-action/publish-pr-report@"
        )
        if f"{expected}{PUBLISHED_RELEASE_SHA}" not in example:
            raise DistributionError(f"{path.name} must pin the published v1.0.0 commit")

    release_notes = root / "docs" / "releases" / "v1.0.0.md"
    notes = release_notes.read_text(encoding="utf-8")
    for heading in (
        "Overview", "Key capabilities", "Supported environment", "Basic usage",
        "Inputs and outputs", "Security considerations", "Known limitations", "Documentation",
    ):
        if f"## {heading}" not in notes:
            raise DistributionError(f"v1.0.0 release notes are missing the {heading} section")
    readme = (root / "README.md").read_text(encoding="utf-8")
    portuguese = (root / "README.pt-BR.md").read_text(encoding="utf-8")
    for document_name, text in (("README.md", readme), ("README.pt-BR.md", portuguese)):
        if f"{ACTION_REF_PREFIX}{PUBLISHED_RELEASE_SHA}" not in text:
            raise DistributionError(f"{document_name} does not pin the published v1.0.0 commit")
        if "@REVIEWED_FULL_40_CHARACTER_SHA" in text or (
            "@0000000000000000000000000000000000000000" in text
        ):
            raise DistributionError(f"{document_name} still contains a pre-release placeholder")
    if "runtime benchmark" not in readme or "complexity-analyzers" not in readme:
        raise DistributionError("README is missing product-scope or analysis-engine discovery text")

    checked_links = validate_links(root)
    return {
        "schemaVersion": "complexity-action-marketplace-readiness/1.0",
        "actionName": action_name,
        "description": description,
        "author": author,
        "branding": {"icon": icon_match.group(1), "color": color_match.group(1)},
        "categories": ["code-quality", "continuous-integration"],
        "inputs": sorted(inputs),
        "outputs": sorted(outputs),
        "examples": sorted(REQUIRED_EXAMPLES),
        "localDocumentationLinksChecked": checked_links,
        "nameUniquenessVerification": "not-verified-by-local-validator",
        "marketplaceListingVerification": "not-verified-by-local-validator",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = validate(root)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except DistributionError as error:
        raise SystemExit(f"distribution validation failed: {error}") from error
