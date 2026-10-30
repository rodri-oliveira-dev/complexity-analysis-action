#!/usr/bin/env bash

set -euo pipefail

tool_command="$TOOL_DIRECTORY/complexity-analysis"
arguments=(
  analyze
  "$ANALYSIS_PATH"
  --format json
  --output "$REPORT_PATH"
)

if [[ "$INCLUDE_GENERATED" == "true" ]]; then
  arguments+=(--include-generated)
fi

if [[ "$DETECT_DUPLICATES" == "true" ]]; then
  arguments+=(--detect-duplicates)
fi

printf 'Running Complexity Analysis...\n'
set +e
"$tool_command" "${arguments[@]}"
exit_code=$?
set -e

if (( exit_code != 0 )); then
  printf 'analysis-status=failed\n' >> "$GITHUB_OUTPUT"
  printf '::error title=Complexity Analysis failed::The CLI exited with code %d. Review the preceding CLI output for details.\n' "$exit_code"
  exit "$exit_code"
fi

if [[ ! -s "$REPORT_PATH" ]]; then
  printf 'analysis-status=failed\n' >> "$GITHUB_OUTPUT"
  printf '::error title=Complexity Analysis failed::The CLI completed without creating a non-empty report at the expected path.\n'
  exit 1
fi

printf 'analysis-status=success\n' >> "$GITHUB_OUTPUT"
printf 'Complexity Analysis report: %s\n' "$REPORT_PATH"
