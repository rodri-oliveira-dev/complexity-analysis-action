#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
test_root="$(mktemp -d "${RUNNER_TEMP:-/tmp}/complexity-regression-e2e.XXXXXX")"
trap 'rm -rf -- "$test_root"' EXIT

workspace="$test_root/controlled-repository"
mkdir -p "$workspace/reports" "$test_root/runner"
git -C "$workspace" init -q
git -C "$workspace" config user.email tests@example.invalid
git -C "$workspace" config user.name "Complexity Tests"

printf '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>\n' \
  > "$workspace/Controlled.csproj"
printf '%s\n' \
  'namespace Controlled;' \
  'public static class Algorithms' \
  '{' \
  '    public static int Count(int[] values)' \
  '    {' \
  '        int total = 0;' \
  '        foreach (int value in values)' \
  '            total += value;' \
  '        return total;' \
  '    }' \
  '}' > "$workspace/Algorithms.cs"
git -C "$workspace" add Controlled.csproj Algorithms.cs
git -C "$workspace" commit -qm baseline
baseline_sha="$(git -C "$workspace" rev-parse HEAD)"

git -C "$workspace" mv Algorithms.cs RenamedAlgorithms.cs
printf '%s\n' \
  'namespace Controlled;' \
  'public static class Algorithms' \
  '{' \
  '    public static int Count(int[] values)' \
  '    {' \
  '        int total = 0;' \
  '        foreach (int left in values)' \
  '            foreach (int right in values)' \
  '                total += left + right;' \
  '        return total;' \
  '    }' \
  '}' > "$workspace/RenamedAlgorithms.cs"
git -C "$workspace" add RenamedAlgorithms.cs
git -C "$workspace" commit -qm regression
git -C "$workspace" remote add origin "$workspace"

install_output="$test_root/install-output"
env GITHUB_OUTPUT="$install_output" RUNNER_TEMP="$test_root/runner" \
  NUGET_CONFIG="$repo_root/nuget.config" TOOL_VERSION=1.0.0 \
  "$repo_root/scripts/install-tool.sh"
tool_command="$(sed -n 's/^tool-command=//p' "$install_output")"

run_once() {
  local name="$1"
  local output="$test_root/$name-output"
  env \
    ACTION_PATH="$repo_root" WORKSPACE="$workspace" RUNNER_TEMP="$test_root/runner" \
    GITHUB_OUTPUT="$output" TOOL_COMMAND="$tool_command" ANALYSIS_STATUS=success \
    ANALYSIS_RELATIVE_PATH=Controlled.csproj COMPARISON_REQUESTED=true BASELINE_INPUT_PATH="" \
    BASELINE_REPORT_PATH="$workspace/reports/baseline.json" CURRENT_REPORT_PATH="$workspace/reports/current.json" \
    COMPARISON_REPORT_PATH="$workspace/reports/comparison.json" COMPARISON_SARIF_PATH="$workspace/reports/comparison.sarif" \
    BASE_REF="$baseline_sha" INCLUDE_GENERATED=false DETECT_DUPLICATES=false GITHUB_EVENT_NAME=push \
    GITHUB_EVENT_PATH="$test_root/no-event.json" GITHUB_REPOSITORY=controlled/repository \
    "$repo_root/scripts/run-comparison.sh"
  grep -Fx 'comparison-status=regressions-detected' "$output" >/dev/null
  grep -Fx 'regression-count=1' "$output" >/dev/null
}

run_once first
first_baseline="$(sha256sum "$workspace/reports/baseline.json" | cut -d' ' -f1)"
first_current="$(sha256sum "$workspace/reports/current.json" | cut -d' ' -f1)"
first_comparison="$(sha256sum "$workspace/reports/comparison.json" | cut -d' ' -f1)"
run_once second
test "$first_baseline" = "$(sha256sum "$workspace/reports/baseline.json" | cut -d' ' -f1)"
test "$first_current" = "$(sha256sum "$workspace/reports/current.json" | cut -d' ' -f1)"
test "$first_comparison" = "$(sha256sum "$workspace/reports/comparison.json" | cut -d' ' -f1)"
python3 "$repo_root/scripts/inspect-comparison.py" "$workspace/reports/comparison.json" | grep -Fx 1 >/dev/null

printf 'Published CLI pull-request regression end-to-end test passed.\n'
