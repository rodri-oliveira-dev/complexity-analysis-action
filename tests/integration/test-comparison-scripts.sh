#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
test_root="$(mktemp -d "${RUNNER_TEMP:-/tmp}/complexity-comparison-tests.XXXXXX")"
trap 'rm -rf -- "$test_root"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

workspace="$test_root/workspace"
mkdir -p "$workspace" "$test_root/runner" "$workspace/reports"
git -C "$workspace" init -q
git -C "$workspace" config user.email tests@example.invalid
git -C "$workspace" config user.name "Complexity Tests"
printf '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>\n' > "$workspace/Sample.csproj"
git -C "$workspace" add Sample.csproj
git -C "$workspace" commit -qm baseline
baseline_sha="$(git -C "$workspace" rev-parse HEAD)"
printf '// current\n' > "$workspace/Program.cs"
git -C "$workspace" add Program.cs
git -C "$workspace" commit -qm current
current_sha="$(git -C "$workspace" rev-parse HEAD)"
git -C "$workspace" remote add origin "$workspace"

baseline_input="$workspace/provided.json"
printf '{"SchemaVersion":"complexity-snapshot/1.0","EntryPoint":"Sample.csproj","Projects":[],"QualityGates":[]}\n' > "$baseline_input"
fake_cli="$repo_root/tests/integration/fake-complexity-analysis.sh"
chmod +x "$fake_cli"

run_comparison() {
  local name="$1"
  local classification="$2"
  local baseline_path="${3-$baseline_input}"
  local base_ref="${4:-}"
  local output="$test_root/$name-output"
  : > "$test_root/invocations"
  env \
    ACTION_PATH="$repo_root" WORKSPACE="$workspace" RUNNER_TEMP="$test_root/runner" \
    GITHUB_OUTPUT="$output" TOOL_COMMAND="$fake_cli" ANALYSIS_STATUS=success \
    ANALYSIS_RELATIVE_PATH=Sample.csproj COMPARISON_REQUESTED=true \
    BASELINE_INPUT_PATH="$baseline_path" BASELINE_REPORT_PATH="$workspace/reports/baseline.json" \
    CURRENT_REPORT_PATH="$workspace/reports/current.json" COMPARISON_REPORT_PATH="$workspace/reports/comparison.json" \
    COMPARISON_SARIF_PATH="$workspace/reports/comparison.sarif" BASE_REF="$base_ref" \
    INCLUDE_GENERATED=false DETECT_DUPLICATES=false GITHUB_EVENT_NAME=push \
    GITHUB_EVENT_PATH="$test_root/no-event.json" GITHUB_REPOSITORY=example/repository \
    COMPLEXITY_ACTION_TEST_INVOCATIONS="$test_root/invocations" \
    COMPLEXITY_ACTION_TEST_COMPARISON_CLASSIFICATION="$classification" \
    GITHUB_TOKEN=must-not-reach-analysis COMPLEXITY_ACTION_TEST_SECRET=must-not-reach-analysis \
    "$repo_root/scripts/run-comparison.sh"
  printf '%s\n' "$output"
}

assert_case() {
  local name="$1"
  local classification="$2"
  local expected_status="$3"
  local expected_count="$4"
  local output="$test_root/$name-output"
  run_comparison "$name" "$classification" >/dev/null
  grep -Fx "comparison-status=$expected_status" "$output" >/dev/null
  grep -Fx "regression-count=$expected_count" "$output" >/dev/null
  grep -Fx 'base-revision-kind=snapshot' "$output" >/dev/null
  grep -Fx 'base-revision=' "$output" >/dev/null
}

assert_case regression regression regressions-detected 1
assert_case unchanged equivalent no-regressions 0
assert_case improvement improvement no-regressions 0
assert_case unknown incomparable no-regressions 0
assert_case added added no-regressions 0
assert_case deleted removed no-regressions 0
# Stable member identity remains comparable when the CLI reports a source-file rename.
assert_case renamed-file equivalent no-regressions 0

invalid_output="$test_root/incompatible-output"
: > "$test_root/invocations"
env \
  ACTION_PATH="$repo_root" WORKSPACE="$workspace" RUNNER_TEMP="$test_root/runner" \
  GITHUB_OUTPUT="$invalid_output" TOOL_COMMAND="$fake_cli" ANALYSIS_STATUS=success \
  ANALYSIS_RELATIVE_PATH=Sample.csproj COMPARISON_REQUESTED=true BASELINE_INPUT_PATH="$baseline_input" \
  BASELINE_REPORT_PATH="$workspace/reports/baseline.json" CURRENT_REPORT_PATH="$workspace/reports/current.json" \
  COMPARISON_REPORT_PATH="$workspace/reports/comparison.json" COMPARISON_SARIF_PATH="$workspace/reports/comparison.sarif" \
  BASE_REF="" INCLUDE_GENERATED=false DETECT_DUPLICATES=false GITHUB_EVENT_NAME=push \
  GITHUB_EVENT_PATH="$test_root/no-event.json" GITHUB_REPOSITORY=example/repository \
  COMPLEXITY_ACTION_TEST_INVOCATIONS="$test_root/invocations" COMPLEXITY_ACTION_TEST_COMPARE_EXIT_CODE=1 \
  GITHUB_TOKEN=must-not-reach-analysis COMPLEXITY_ACTION_TEST_SECRET=must-not-reach-analysis \
  "$repo_root/scripts/run-comparison.sh"
grep -Fx 'comparison-status=failed' "$invalid_output" >/dev/null

missing_output="$test_root/missing-baseline-output"
run_comparison missing-baseline equivalent "" "" >/dev/null
grep -Fx 'comparison-status=unavailable' "$missing_output" >/dev/null
invalid_ref_output="$test_root/invalid-ref-output"
run_comparison invalid-ref equivalent "" refs/heads/does-not-exist >/dev/null
grep -Fx 'comparison-status=unavailable' "$invalid_ref_output" >/dev/null

# A fork PR event may fetch its exact head through refs/pull/N/head while the
# base comes from the base repository, even when neither object is in a shallow checkout.
origin="$test_root/origin.git"
git clone -q --bare "$workspace" "$origin"
git -C "$origin" update-ref refs/pull/7/head "$current_sha"
shallow="$test_root/shallow"
git clone -q --depth=1 --branch master "file://$origin" "$shallow"
git -C "$shallow" checkout -q "$current_sha"
mkdir -p "$shallow/reports"
event_path="$test_root/event.json"
printf '{"pull_request":{"number":7,"base":{"sha":"%s","ref":"master","repo":{"full_name":"base/repository"}},"head":{"sha":"%s","repo":{"full_name":"fork/repository"}}}}\n' \
  "$baseline_sha" "$current_sha" > "$event_path"
fork_output="$test_root/fork-output"
: > "$test_root/invocations"
env \
  ACTION_PATH="$repo_root" WORKSPACE="$shallow" RUNNER_TEMP="$test_root/runner" \
  GITHUB_OUTPUT="$fork_output" TOOL_COMMAND="$fake_cli" ANALYSIS_STATUS=success \
  ANALYSIS_RELATIVE_PATH=Sample.csproj COMPARISON_REQUESTED=true BASELINE_INPUT_PATH="" \
  BASELINE_REPORT_PATH="$shallow/reports/baseline.json" CURRENT_REPORT_PATH="$shallow/reports/current.json" \
  COMPARISON_REPORT_PATH="$shallow/reports/comparison.json" COMPARISON_SARIF_PATH="$shallow/reports/comparison.sarif" \
  BASE_REF="" INCLUDE_GENERATED=false DETECT_DUPLICATES=false GITHUB_EVENT_NAME=pull_request \
  GITHUB_EVENT_PATH="$event_path" GITHUB_REPOSITORY=base/repository \
  COMPLEXITY_ACTION_TEST_INVOCATIONS="$test_root/invocations" \
  COMPLEXITY_ACTION_TEST_COMPARISON_CLASSIFICATION=equivalent \
  GITHUB_TOKEN=must-not-reach-analysis COMPLEXITY_ACTION_TEST_SECRET=must-not-reach-analysis \
  "$repo_root/scripts/run-comparison.sh"
grep -Fx 'comparison-status=no-regressions' "$fork_output" >/dev/null
grep -Fx 'base-revision-kind=commit' "$fork_output" >/dev/null
grep -Fx "base-revision=$baseline_sha" "$fork_output" >/dev/null
test -s "$shallow/reports/baseline.json"
test -s "$shallow/reports/current.json"

printf 'All comparison script integration tests passed.\n'
