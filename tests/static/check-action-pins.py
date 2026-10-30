#!/usr/bin/env python3

import re
import sys
from pathlib import Path


PINNED_ACTION = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def main() -> None:
    errors: list[str] = []
    for value in sys.argv[1:]:
        path = Path(value)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"^\s*-?\s*uses:\s*([^\s#]+)", line)
            if not match:
                continue
            reference = match.group(1)
            if reference == "./" or PINNED_ACTION.fullmatch(reference):
                continue
            errors.append(f"{path}:{number}: action reference is not pinned to a full commit SHA: {reference}")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
