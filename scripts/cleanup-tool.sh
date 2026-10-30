#!/usr/bin/env bash

set -euo pipefail

fail() {
  printf '::error title=Complexity Analysis cleanup failed::%s\n' "$1"
  exit 1
}

[[ -n "${RUNNER_TEMP:-}" ]] || fail "RUNNER_TEMP is not available."
[[ -n "${TOOL_DIRECTORY:-}" ]] || exit 0

runner_temp="$(realpath -e -- "$RUNNER_TEMP")" || fail "RUNNER_TEMP does not exist."
tool_directory="$(realpath -e -- "$TOOL_DIRECTORY")" || exit 0
case "$tool_directory" in
  "$runner_temp"/complexity-analysis-tool.*) ;;
  *) fail "Refusing to remove a CLI directory outside the expected runner temporary path." ;;
esac

rm -rf -- "$tool_directory"
