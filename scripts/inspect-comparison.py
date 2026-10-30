#!/usr/bin/env python3

import argparse
from pathlib import Path

from pr_reporting import ReportError, load_json, validate_comparison


def fail(message: str) -> None:
    print(f"::error title=Complexity comparison report validation failed::{message}")
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        _, counts = validate_comparison(load_json(args.path))
    except ReportError as error:
        fail(str(error))
    print(counts["regression"])


if __name__ == "__main__":
    main()
