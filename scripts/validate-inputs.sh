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
: "${INPUT_COMPARE_WITH_BASE:=false}"
: "${INPUT_BASE_REF:=}"
: "${INPUT_FAIL_ON_REGRESSION:=false}"
: "${INPUT_BASELINE_PATH:=}"
: "${INPUT_COMPARISON_OUTPUT:=}"
: "${INPUT_COMMENT_ON_PR:=false}"

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
[[ -n "${GITHUB_OUTPUT:-}" ]] || fail "GITHUB_OUTPUT is not available."
[[ "${GITHUB_EVENT_NAME:-}" != "pull_request_target" ]] ||
  fail "pull_request_target is not supported because project evaluation must not run in a privileged PR context."
workspace="$(realpath -e -- "$GITHUB_WORKSPACE")" || fail "GITHUB_WORKSPACE does not exist."

for value_name in INPUT_PATH INPUT_TOOL_VERSION INPUT_OUTPUT_DIRECTORY; do
  value="${!value_name:-}"
  [[ -n "$value" ]] || fail "${value_name#INPUT_} must not be empty."
  contains_line_break "$value" && fail "${value_name#INPUT_} must not contain line breaks."
done

semver_pattern='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'
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
[[ "$INPUT_COMPARE_WITH_BASE" == "true" || "$INPUT_COMPARE_WITH_BASE" == "false" ]] ||
  fail "compare-with-base must be either 'true' or 'false'."
[[ "$INPUT_FAIL_ON_REGRESSION" == "true" || "$INPUT_FAIL_ON_REGRESSION" == "false" ]] ||
  fail "fail-on-regression must be either 'true' or 'false'."
[[ "$INPUT_COMMENT_ON_PR" == "true" || "$INPUT_COMMENT_ON_PR" == "false" ]] ||
  fail "comment-on-pr must be either 'true' or 'false'."
if [[ "$INPUT_COMMENT_ON_PR" == "true" ]]; then
  [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]] ||
    fail "comment-on-pr=true requires the pull_request event."
  [[ "$INPUT_COMPARE_WITH_BASE" == "true" || -n "$INPUT_BASELINE_PATH" ]] ||
    fail "comment-on-pr=true requires a baseline comparison."
fi

for value_name in INPUT_BASE_REF INPUT_BASELINE_PATH INPUT_COMPARISON_OUTPUT; do
  value="${!value_name:-}"
  contains_line_break "$value" && fail "${value_name#INPUT_} must not contain line breaks."
done

if [[ -n "$INPUT_BASE_REF" ]]; then
  [[ "$INPUT_COMPARE_WITH_BASE" == "true" ]] ||
    fail "base-ref requires compare-with-base=true."
  [[ "$INPUT_BASE_REF" != -* && "$INPUT_BASE_REF" != *'..'* && "$INPUT_BASE_REF" != *'@{'* ]] ||
    fail "base-ref is not a safe Git reference."
  [[ "$INPUT_BASE_REF" =~ ^[0-9A-Za-z._/+@{}-]+$ ]] ||
    fail "base-ref contains unsupported characters."
fi
[[ -z "$INPUT_BASE_REF" || -z "$INPUT_BASELINE_PATH" ]] ||
  fail "base-ref and baseline-path are mutually exclusive baseline sources."
if [[ "$INPUT_FAIL_ON_REGRESSION" == "true" ]]; then
  [[ "$INPUT_COMPARE_WITH_BASE" == "true" || -n "$INPUT_BASELINE_PATH" ]] ||
    fail "fail-on-regression requires compare-with-base=true or baseline-path."
fi

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

case "$INPUT_MAX_COMPLEXITY" in
  ""|constant|log_n|linear|n|n_log_n|quadratic|n2|cubic|n3|exponential|factorial) ;;
  *) fail "max-complexity is not a supported Big-O value." ;;
esac

positive_integer_pattern='^[1-9][0-9]*$'
non_negative_integer_pattern='^(0|[1-9][0-9]*)$'
for value_name in INPUT_MAX_CYCLOMATIC_COMPLEXITY INPUT_MAX_METHOD_NLOC; do
  value="${!value_name:-}"
  [[ -z "$value" || "$value" =~ $positive_integer_pattern ]] ||
    fail "${value_name#INPUT_} must be a positive integer."
done
for value_name in INPUT_MAX_COGNITIVE_COMPLEXITY INPUT_MAX_NESTING_DEPTH INPUT_MAX_DUPLICATE_RATE; do
  value="${!value_name:-}"
  [[ -z "$value" || "$value" =~ $non_negative_integer_pattern ]] ||
    fail "${value_name#INPUT_} must be a non-negative integer."
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
[[ "$output_directory" != "$workspace/.git" && "$output_directory" != "$workspace/.git/"* ]] ||
  fail "output-directory must not be inside the repository's .git directory."
[[ ! -e "$output_directory" || -d "$output_directory" ]] ||
  fail "The provided output-directory is not a directory."

mkdir -p -- "$output_directory" || fail "Unable to create output-directory."
output_directory="$(realpath -e -- "$output_directory")" ||
  fail "Unable to resolve the created output-directory."
is_within_workspace "$output_directory" ||
  fail "output-directory resolves outside GITHUB_WORKSPACE through a symbolic link."

report_path="$output_directory/complexity-analysis-report.json"
sarif_path="$output_directory/complexity-analysis-report.sarif"
analysis_relative_path="${analysis_path#"$workspace/"}"
output_relative_path="${output_directory#"$workspace/"}"

comparison_requested=false
if [[ "$INPUT_COMPARE_WITH_BASE" == "true" || -n "$INPUT_BASELINE_PATH" ]]; then
  comparison_requested=true
fi

baseline_input_path=""
if [[ -n "$INPUT_BASELINE_PATH" ]]; then
  baseline_candidate="$(resolve_from_workspace "$INPUT_BASELINE_PATH")"
  baseline_input_path="$(realpath -e -- "$baseline_candidate" 2>/dev/null)" ||
    fail "The provided baseline-path does not exist."
  [[ -f "$baseline_input_path" ]] || fail "baseline-path must reference a JSON file."
  is_within_workspace "$baseline_input_path" || fail "baseline-path must resolve within GITHUB_WORKSPACE."
  [[ "${baseline_input_path,,}" == *.json ]] || fail "baseline-path must reference a .json file."
fi

if [[ -n "$INPUT_COMPARISON_OUTPUT" ]]; then
  comparison_candidate="$(resolve_from_workspace "$INPUT_COMPARISON_OUTPUT")"
else
  comparison_candidate="$output_directory/comparison.json"
fi
comparison_path="$(realpath -m -- "$comparison_candidate")" ||
  fail "Unable to resolve comparison-output."
is_within_workspace "$comparison_path" || fail "comparison-output must resolve within GITHUB_WORKSPACE."
[[ "$comparison_path" != "$workspace" && "${comparison_path,,}" == *.json ]] ||
  fail "comparison-output must reference a .json file."
[[ "$comparison_path" != "$workspace/.git" && "$comparison_path" != "$workspace/.git/"* ]] ||
  fail "comparison-output must not be inside the repository's .git directory."
comparison_parent="$(dirname -- "$comparison_path")"
mkdir -p -- "$comparison_parent" || fail "Unable to create the comparison-output directory."
comparison_parent="$(realpath -e -- "$comparison_parent")" ||
  fail "Unable to resolve the comparison-output directory."
is_within_workspace "$comparison_parent" ||
  fail "comparison-output resolves outside GITHUB_WORKSPACE through a symbolic link."
comparison_path="$comparison_parent/$(basename -- "$comparison_path")"

baseline_report_path="$output_directory/baseline.json"
current_report_path="$output_directory/current.json"
comparison_sarif_path="${comparison_path%.json}.sarif"
pr_report_path="$output_directory/pr-report.json"
for reserved_path in "$report_path" "$sarif_path" "$baseline_report_path" "$current_report_path" "$pr_report_path"; do
  [[ "$comparison_path" != "$reserved_path" && "$comparison_sarif_path" != "$reserved_path" ]] ||
    fail "comparison-output conflicts with another report path."
done

{
  printf 'analysis-path=%s\n' "$analysis_path"
  printf 'analysis-relative-path=%s\n' "$analysis_relative_path"
  printf 'output-relative-path=%s\n' "$output_relative_path"
  printf 'report-path=%s\n' "$report_path"
  printf 'sarif-path=%s\n' "$sarif_path"
  printf 'tool-version=%s\n' "$INPUT_TOOL_VERSION"
  printf 'has-thresholds=%s\n' "$has_thresholds"
  printf 'comparison-requested=%s\n' "$comparison_requested"
  printf 'baseline-input-path=%s\n' "$baseline_input_path"
  printf 'baseline-report-path=%s\n' "$baseline_report_path"
  printf 'current-report-path=%s\n' "$current_report_path"
  printf 'comparison-report-path=%s\n' "$comparison_path"
  printf 'comparison-sarif-path=%s\n' "$comparison_sarif_path"
  printf 'pr-report-path=%s\n' "$pr_report_path"
} >> "$GITHUB_OUTPUT"

printf 'Validated analysis input: %s\n' "$analysis_path"
printf 'Report destination: %s\n' "$report_path"
printf 'SARIF destination: %s\n' "$sarif_path"
