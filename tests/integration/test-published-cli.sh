#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
test_root="$(mktemp -d "${RUNNER_TEMP:-/tmp}/complexity-published-cli.XXXXXX")"
trap 'rm -rf -- "$test_root"' EXIT

export RUNNER_OS=Linux
export GITHUB_WORKSPACE="$repo_root"
export RUNNER_TEMP="$test_root"
export ACTION_PATH="$repo_root"

validation_output="$test_root/validation-output"
env \
  GITHUB_OUTPUT="$validation_output" \
  INPUT_PATH="tests/fixtures/Sample Project/Sample Project.slnx" \
  INPUT_TOOL_VERSION=1.0.1 \
  INPUT_OUTPUT_DIRECTORY="artifacts/published CLI integration" \
  INPUT_INCLUDE_GENERATED=false \
  INPUT_DETECT_DUPLICATES=true \
  INPUT_MAX_COMPLEXITY=factorial \
  INPUT_MAX_CYCLOMATIC_COMPLEXITY=100 \
  INPUT_MAX_COGNITIVE_COMPLEXITY=100 \
  INPUT_MAX_NESTING_DEPTH=100 \
  INPUT_MAX_METHOD_NLOC=1000 \
  INPUT_MAX_DUPLICATE_RATE=100 \
  INPUT_FAIL_ON_QUALITY_GATE=true \
  INPUT_UPLOAD_SARIF=false \
  "$repo_root/scripts/validate-inputs.sh"

install_output="$test_root/install-output"
env \
  GITHUB_OUTPUT="$install_output" \
  NUGET_CONFIG="$repo_root/nuget.config" \
  TOOL_VERSION=1.0.1 \
  "$repo_root/scripts/install-tool.sh"
tool_command="$(sed -n 's/^tool-command=//p' "$install_output")"

analysis_output="$test_root/analysis-output"
report_path="$repo_root/artifacts/published CLI integration/complexity-analysis-report.json"
sarif_path="$repo_root/artifacts/published CLI integration/complexity-analysis-report.sarif"
env \
  GITHUB_OUTPUT="$analysis_output" \
  TOOL_COMMAND="$tool_command" \
  ANALYSIS_PATH="$repo_root/tests/fixtures/Sample Project/Sample Project.slnx" \
  ANALYSIS_RELATIVE_PATH="tests/fixtures/Sample Project/Sample Project.slnx" \
  OUTPUT_RELATIVE_PATH="artifacts/published CLI integration" \
  WORKSPACE="$repo_root" \
  REPORT_PATH="$report_path" \
  SARIF_PATH="$sarif_path" \
  INCLUDE_GENERATED=false \
  DETECT_DUPLICATES=true \
  MAX_COMPLEXITY=factorial \
  MAX_CYCLOMATIC_COMPLEXITY=100 \
  MAX_COGNITIVE_COMPLEXITY=100 \
  MAX_NESTING_DEPTH=100 \
  MAX_METHOD_NLOC=1000 \
  MAX_DUPLICATE_RATE=100 \
  HAS_THRESHOLDS=true \
  "$repo_root/scripts/run-analysis.sh"

grep -Fx 'analysis-status=success' "$analysis_output" >/dev/null
grep -Fx 'quality-gate-status=passed' "$analysis_output" >/dev/null
python3 "$repo_root/scripts/validate-report.py" json "$report_path"
python3 "$repo_root/scripts/validate-report.py" sarif "$sarif_path"
[[ -z "$(find "$repo_root/tests" -type d \( -name obj -o -name bin \) -print -quit)" ]]

printf 'Published CLI integration test passed.\n'
