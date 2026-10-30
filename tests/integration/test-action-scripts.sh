#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
test_root="$(mktemp -d "${RUNNER_TEMP:-/tmp}/complexity-action-tests.XXXXXX")"
trap 'rm -rf -- "$test_root"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

workspace="$test_root/workspace with spaces"
mkdir -p "$workspace/Sample Project" "$test_root/runner"
cp "$repo_root/tests/fixtures/Sample Project/Sample Project.csproj" "$workspace/Sample Project/"
cp "$repo_root/tests/fixtures/Sample Project/Program.cs" "$workspace/Sample Project/"

validation_output="$test_root/validation-output"
env \
  RUNNER_OS=Linux \
  GITHUB_WORKSPACE="$workspace" \
  GITHUB_OUTPUT="$validation_output" \
  INPUT_PATH="Sample Project/Sample Project.csproj" \
  INPUT_TOOL_VERSION=1.0.0 \
  INPUT_OUTPUT_DIRECTORY="reports with spaces" \
  INPUT_INCLUDE_GENERATED=false \
  INPUT_DETECT_DUPLICATES=true \
  INPUT_FAIL_ON_QUALITY_GATE=true \
  INPUT_UPLOAD_SARIF=false \
  "$repo_root/scripts/validate-inputs.sh"
grep -F "analysis-path=$workspace/Sample Project/Sample Project.csproj" "$validation_output" >/dev/null

injection_output="$test_root/injection-output"
env \
  RUNNER_OS=Linux \
  GITHUB_WORKSPACE="$workspace" \
  GITHUB_OUTPUT="$injection_output" \
  INPUT_PATH="Sample Project/Sample Project.csproj" \
  INPUT_TOOL_VERSION=1.0.0 \
  INPUT_OUTPUT_DIRECTORY='reports; touch injected' \
  INPUT_INCLUDE_GENERATED=false \
  INPUT_DETECT_DUPLICATES=false \
  INPUT_FAIL_ON_QUALITY_GATE=true \
  INPUT_UPLOAD_SARIF=false \
  "$repo_root/scripts/validate-inputs.sh"
[[ -d "$workspace/reports; touch injected" ]]
[[ ! -e "$workspace/injected" ]]

if env \
  RUNNER_OS=Linux GITHUB_WORKSPACE="$workspace" GITHUB_OUTPUT="$test_root/invalid-output" \
  INPUT_PATH=missing.csproj INPUT_TOOL_VERSION=1.0.0 INPUT_OUTPUT_DIRECTORY=reports \
  INPUT_INCLUDE_GENERATED=false INPUT_DETECT_DUPLICATES=false \
  INPUT_FAIL_ON_QUALITY_GATE=true INPUT_UPLOAD_SARIF=false \
  "$repo_root/scripts/validate-inputs.sh"; then
  fail "invalid project path was accepted"
fi

if env \
  RUNNER_OS=Linux GITHUB_WORKSPACE="$workspace" GITHUB_OUTPUT="$test_root/git-output" \
  INPUT_PATH="Sample Project/Sample Project.csproj" INPUT_TOOL_VERSION=1.0.0 INPUT_OUTPUT_DIRECTORY=.git/reports \
  INPUT_INCLUDE_GENERATED=false INPUT_DETECT_DUPLICATES=false \
  INPUT_FAIL_ON_QUALITY_GATE=true INPUT_UPLOAD_SARIF=false \
  "$repo_root/scripts/validate-inputs.sh"; then
  fail ".git output path was accepted"
fi

fake_cli="$repo_root/tests/integration/fake-complexity-analysis.sh"
chmod +x "$fake_cli"
report="$test_root/report with spaces.json"
sarif="$test_root/report with spaces.sarif"

run_analysis() {
  local exit_code="$1"
  local has_thresholds="$2"
  local output="$3"
  local output_relative="${5:-reports with spaces}"
  : > "$test_root/invocations"
  env \
    ACTION_PATH="$repo_root" \
    TOOL_COMMAND="$fake_cli" \
    RUNNER_TEMP="$test_root/runner" \
    GITHUB_OUTPUT="$output" \
    ANALYSIS_PATH="$workspace/Sample Project/Sample Project.csproj" \
    ANALYSIS_RELATIVE_PATH="Sample Project/Sample Project.csproj" \
    OUTPUT_RELATIVE_PATH="$output_relative" \
    WORKSPACE="$workspace" \
    REPORT_PATH="$report" \
    SARIF_PATH="$sarif" \
    INCLUDE_GENERATED=false \
    DETECT_DUPLICATES=true \
    MAX_COMPLEXITY="" \
    MAX_CYCLOMATIC_COMPLEXITY="${4:-}" \
    MAX_COGNITIVE_COMPLEXITY="" \
    MAX_NESTING_DEPTH="" \
    MAX_METHOD_NLOC="" \
    MAX_DUPLICATE_RATE="" \
    HAS_THRESHOLDS="$has_thresholds" \
    FAKE_EXIT_CODE="$exit_code" \
    FAKE_INVOCATIONS="$test_root/invocations" \
    "$repo_root/scripts/run-analysis.sh"
}

run_analysis 0 false "$test_root/success-output"
grep -Fx 'analysis-status=success' "$test_root/success-output" >/dev/null
grep -Fx 'quality-gate-status=not-configured' "$test_root/success-output" >/dev/null
grep -F '|json|true' "$test_root/invocations" >/dev/null
python3 "$repo_root/scripts/validate-report.py" json "$report"
python3 "$repo_root/scripts/validate-report.py" sarif "$sarif"

# The output directory may also contain the selected project. Only stale report
# files may be omitted from the isolated copy; excluding the directory breaks it.
run_analysis 0 false "$test_root/overlap-output" "" "Sample Project"
grep -Fx 'analysis-status=success' "$test_root/overlap-output" >/dev/null

run_analysis 0 true "$test_root/passing-output" 100
grep -Fx 'quality-gate-status=passed' "$test_root/passing-output" >/dev/null

run_analysis 2 true "$test_root/gate-output" 1
grep -Fx 'analysis-status=success' "$test_root/gate-output" >/dev/null
grep -Fx 'quality-gate-status=failed' "$test_root/gate-output" >/dev/null
grep -Fx 'analysis-exit-code=2' "$test_root/gate-output" >/dev/null

if env ANALYSIS_EXIT_CODE=2 FAIL_ON_QUALITY_GATE=true UPLOAD_SARIF=false \
  SARIF_VALIDATION_OUTCOME=skipped SARIF_UPLOAD_OUTCOME=skipped \
  "$repo_root/scripts/apply-result.sh"; then
  fail "blocking quality-gate failure was accepted"
fi
env ANALYSIS_EXIT_CODE=2 FAIL_ON_QUALITY_GATE=false UPLOAD_SARIF=false \
  SARIF_VALIDATION_OUTCOME=skipped SARIF_UPLOAD_OUTCOME=skipped \
  "$repo_root/scripts/apply-result.sh"

run_analysis 1 false "$test_root/error-output"
grep -Fx 'analysis-status=failed' "$test_root/error-output" >/dev/null
grep -Fx 'analysis-exit-code=1' "$test_root/error-output" >/dev/null

run_analysis 130 false "$test_root/cancel-output"
grep -Fx 'analysis-status=canceled' "$test_root/cancel-output" >/dev/null
grep -Fx 'analysis-exit-code=130' "$test_root/cancel-output" >/dev/null

mkdir -p "$test_root/failing-bin"
printf '#!/usr/bin/env bash\nexit 1\n' > "$test_root/failing-bin/dotnet"
chmod +x "$test_root/failing-bin/dotnet"
if env \
  PATH="$test_root/failing-bin:$PATH" \
  RUNNER_TEMP="$test_root/runner" \
  GITHUB_OUTPUT="$test_root/install-output" \
  NUGET_CONFIG="$repo_root/nuget.config" \
  TOOL_VERSION=1.0.0 \
  "$repo_root/scripts/install-tool.sh"; then
  fail "CLI installation failure was accepted"
fi

printf 'All Action script integration tests passed.\n'
