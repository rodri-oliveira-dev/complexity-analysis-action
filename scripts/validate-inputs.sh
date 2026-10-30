#!/usr/bin/env bash

set -euo pipefail

: "${INPUT_MAX_COMPLEXITY:=}"
: "${INPUT_MAX_CYCLOMATIC_COMPLEXITY:=}"
: "${INPUT_MAX_COGNITIVE_COMPLEXITY:=}"
: "${INPUT_MAX_NESTING_DEPTH:=}"
: "${INPUT_MAX_METHOD_NLOC:=}"
: "${INPUT_MAX_DUPLICATE_RATE:=}"
: "${INPUT_FAIL_ON_QUALITY_GATE:=true}"
: "${INPUT_UPLOAD_SARIF:=false}"

fail() {
  printf '::error title=Complexity Analysis input error::%s\n' "$1"
  exit 1
}

contains_line_break() {
  [[ "$1" == *$'\n'* || "$1" == *$'\r'* ]]
}

resolve_from_workspace() {
  local value="$1"
  if [[ "$value" == /* ]]; then
    printf '%s\n' "$value"
  else
    printf '%s/%s\n' "$workspace" "$value"
  fi
}

is_within_workspace() {
  [[ "$1" == "$workspace" || "$1" == "$workspace/"* ]]
}

[[ "${RUNNER_OS:-}" == "Linux" ]] ||
  fail "Unsupported runner '${RUNNER_OS:-unknown}'. This version supports ubuntu-latest only."

[[ -r /etc/os-release ]] ||
  fail "Unable to identify the Linux distribution. This version supports ubuntu-latest only."

# shellcheck disable=SC1091
. /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] ||
  fail "Unsupported Linux distribution '${ID:-unknown}'. This version supports ubuntu-latest only."

[[ -n "${GITHUB_WORKSPACE:-}" ]] || fail "GITHUB_WORKSPACE is not available."
workspace="$(realpath -e -- "$GITHUB_WORKSPACE")" || fail "GITHUB_WORKSPACE does not exist."

for value_name in INPUT_PATH INPUT_TOOL_VERSION INPUT_OUTPUT_DIRECTORY; do
  value="${!value_name:-}"
  [[ -n "$value" ]] || fail "${value_name#INPUT_} must not be empty."
  contains_line_break "$value" && fail "${value_name#INPUT_} must not contain line breaks."
done

semver_pattern='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'
[[ "$INPUT_TOOL_VERSION" =~ $semver_pattern ]] ||
  fail "tool-version must be an exact semantic version such as 1.0.0."

[[ "$INPUT_INCLUDE_GENERATED" == "true" || "$INPUT_INCLUDE_GENERATED" == "false" ]] ||
  fail "include-generated must be either 'true' or 'false'."
[[ "$INPUT_DETECT_DUPLICATES" == "true" || "$INPUT_DETECT_DUPLICATES" == "false" ]] ||
  fail "detect-duplicates must be either 'true' or 'false'."
[[ "$INPUT_FAIL_ON_QUALITY_GATE" == "true" || "$INPUT_FAIL_ON_QUALITY_GATE" == "false" ]] ||
  fail "fail-on-quality-gate must be either 'true' or 'false'."
[[ "$INPUT_UPLOAD_SARIF" == "true" || "$INPUT_UPLOAD_SARIF" == "false" ]] ||
  fail "upload-sarif must be either 'true' or 'false'."

threshold_names=(
  INPUT_MAX_COMPLEXITY
  INPUT_MAX_CYCLOMATIC_COMPLEXITY
  INPUT_MAX_COGNITIVE_COMPLEXITY
  INPUT_MAX_NESTING_DEPTH
  INPUT_MAX_METHOD_NLOC
  INPUT_MAX_DUPLICATE_RATE
)
has_thresholds=false
for value_name in "${threshold_names[@]}"; do
  value="${!value_name:-}"
  contains_line_break "$value" && fail "${value_name#INPUT_} must not contain line breaks."
  if [[ -n "$value" ]]; then
    has_thresholds=true
  fi
done

input_candidate="$(resolve_from_workspace "$INPUT_PATH")"
analysis_path="$(realpath -e -- "$input_candidate" 2>/dev/null)" ||
  fail "The provided path does not exist."
[[ -f "$analysis_path" ]] || fail "The provided path is not a file."
is_within_workspace "$analysis_path" || fail "path must resolve within GITHUB_WORKSPACE."

case "${analysis_path,,}" in
  *.csproj|*.sln|*.slnx) ;;
  *) fail "path must reference a .csproj, .sln, or .slnx file." ;;
esac

output_candidate="$(resolve_from_workspace "$INPUT_OUTPUT_DIRECTORY")"
output_directory="$(realpath -m -- "$output_candidate")" ||
  fail "Unable to resolve output-directory."
is_within_workspace "$output_directory" || fail "output-directory must resolve within GITHUB_WORKSPACE."
[[ "$output_directory" != "$workspace" ]] ||
  fail "output-directory must not be the workspace root."
[[ ! -e "$output_directory" || -d "$output_directory" ]] ||
  fail "The provided output-directory is not a directory."

mkdir -p -- "$output_directory" || fail "Unable to create output-directory."
output_directory="$(realpath -e -- "$output_directory")" ||
  fail "Unable to resolve the created output-directory."
is_within_workspace "$output_directory" ||
  fail "output-directory resolves outside GITHUB_WORKSPACE through a symbolic link."

report_path="$output_directory/complexity-analysis-report.json"
sarif_path="$output_directory/complexity-analysis-report.sarif"

{
  printf 'analysis-path=%s\n' "$analysis_path"
  printf 'report-path=%s\n' "$report_path"
  printf 'sarif-path=%s\n' "$sarif_path"
  printf 'tool-version=%s\n' "$INPUT_TOOL_VERSION"
  printf 'has-thresholds=%s\n' "$has_thresholds"
} >> "$GITHUB_OUTPUT"

printf 'Validated analysis input: %s\n' "$analysis_path"
printf 'Report destination: %s\n' "$report_path"
printf 'SARIF destination: %s\n' "$sarif_path"
