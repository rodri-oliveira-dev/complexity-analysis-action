#!/usr/bin/env bash

set -u -o pipefail

for required_name in ACTION_PATH WORKSPACE RUNNER_TEMP GITHUB_OUTPUT TOOL_COMMAND ANALYSIS_RELATIVE_PATH; do
  if [[ -z "${!required_name:-}" ]]; then
    printf '::error title=Complexity comparison failed::%s is not available.\n' "$required_name"
    exit 1
  fi
done

emit_result() {
  local status="$1"
  local count="$2"
  local exit_code="$3"
  {
    printf 'comparison-status=%s\n' "$status"
    printf 'regression-count=%s\n' "$count"
    printf 'comparison-exit-code=%s\n' "$exit_code"
    printf 'base-revision=%s\n' "${baseline_sha:-}"
    printf 'head-revision=%s\n' "${current_sha:-}"
  } >> "$GITHUB_OUTPUT"
}

unavailable() {
  printf '::error title=Complexity comparison unavailable::%s\n' "$1"
  emit_result unavailable 0 1
  exit 0
}

failed() {
  printf '::error title=Complexity comparison failed::%s\n' "$1"
  emit_result failed 0 1
  exit 0
}

if [[ "${COMPARISON_REQUESTED:-false}" != "true" ]]; then
  emit_result not-requested 0 0
  exit 0
fi

if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request_target" ]]; then
  unavailable "pull_request_target is intentionally unsupported for untrusted project evaluation."
fi

if [[ "${ANALYSIS_STATUS:-}" != "success" ]]; then
  unavailable "The current analysis did not succeed, so snapshots were not compared."
fi

if [[ ! -x "$TOOL_COMMAND" ]]; then
  failed "The installed CLI command is unavailable."
fi

if ! git -c core.hooksPath=/dev/null -C "$WORKSPACE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  unavailable "GITHUB_WORKSPACE is not a Git worktree."
fi

comparison_temp="$(mktemp -d "$RUNNER_TEMP/complexity-comparison.XXXXXX")" ||
  failed "Unable to create isolated comparison storage."
baseline_worktree=""
current_worktree=""

cleanup() {
  if [[ -n "$baseline_worktree" ]]; then
    git -c core.hooksPath=/dev/null -C "$WORKSPACE" worktree remove --force "$baseline_worktree" >/dev/null 2>&1 || true
  fi
  if [[ -n "$current_worktree" ]]; then
    git -c core.hooksPath=/dev/null -C "$WORKSPACE" worktree remove --force "$current_worktree" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$comparison_temp"
}
trap cleanup EXIT

preserved_baseline_input=""
if [[ -n "${BASELINE_INPUT_PATH:-}" ]]; then
  preserved_baseline_input="$comparison_temp/provided-baseline.json"
  cp -- "$BASELINE_INPUT_PATH" "$preserved_baseline_input" ||
    failed "The provided baseline snapshot could not be read."
fi
rm -f -- "$BASELINE_REPORT_PATH" "$CURRENT_REPORT_PATH" "$COMPARISON_REPORT_PATH" "$COMPARISON_SARIF_PATH"

is_sha() {
  [[ "$1" =~ ^[0-9a-fA-F]{40}$ ]]
}

ensure_commit() {
  local sha="$1"
  local fallback_ref="${2:-}"
  if git -c core.hooksPath=/dev/null -C "$WORKSPACE" cat-file -e "$sha^{commit}" 2>/dev/null; then
    return 0
  fi
  git -c core.hooksPath=/dev/null -C "$WORKSPACE" fetch --no-tags --depth=1 origin "$sha" >/dev/null 2>&1 || true
  if git -c core.hooksPath=/dev/null -C "$WORKSPACE" cat-file -e "$sha^{commit}" 2>/dev/null; then
    return 0
  fi
  if [[ -n "$fallback_ref" ]]; then
    git -c core.hooksPath=/dev/null -C "$WORKSPACE" fetch --no-tags --depth=1 origin "$fallback_ref" >/dev/null 2>&1 || true
  fi
  git -c core.hooksPath=/dev/null -C "$WORKSPACE" cat-file -e "$sha^{commit}" 2>/dev/null
}

resolve_explicit_base() {
  local candidate=""
  candidate="$(git -c core.hooksPath=/dev/null -C "$WORKSPACE" rev-parse --verify "${BASE_REF}^{commit}" 2>/dev/null)" || true
  if ! is_sha "$candidate"; then
    git -c core.hooksPath=/dev/null -C "$WORKSPACE" fetch --no-tags --depth=1 origin "$BASE_REF" >/dev/null 2>&1 || return 1
    candidate="$(git -c core.hooksPath=/dev/null -C "$WORKSPACE" rev-parse --verify 'FETCH_HEAD^{commit}' 2>/dev/null)" || return 1
  fi
  is_sha "$candidate" || return 1
  printf '%s\n' "$candidate"
}

read_pr_context() {
  python3 - "$GITHUB_EVENT_PATH" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        event = json.load(stream)
    pull = event["pull_request"]
    print(pull["base"]["sha"])
    print(pull["head"]["sha"])
    print(pull["base"]["repo"]["full_name"])
    print(pull["head"]["repo"]["full_name"])
    print(pull["number"])
    print(pull["base"]["ref"])
except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
    raise SystemExit(1)
PY
}

baseline_sha=""
current_sha=""
base_fallback_ref=""
head_fallback_ref=""

if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
  mapfile -t pr_context < <(read_pr_context) || unavailable "The pull_request event payload is missing required revision data."
  ((${#pr_context[@]} == 6)) || unavailable "The pull_request event payload is incomplete."
  event_base_sha="${pr_context[0]}"
  current_sha="${pr_context[1]}"
  base_repository="${pr_context[2]}"
  head_repository="${pr_context[3]}"
  pull_number="${pr_context[4]}"
  base_branch="${pr_context[5]}"
  if ! is_sha "$event_base_sha" || ! is_sha "$current_sha"; then
    unavailable "The pull_request event contains an invalid commit SHA."
  fi
  [[ "$base_repository" == "${GITHUB_REPOSITORY:-}" ]] ||
    unavailable "The event base repository does not match GITHUB_REPOSITORY."
  [[ "$head_repository" =~ ^[0-9A-Za-z_.-]+/[0-9A-Za-z_.-]+$ ]] ||
    unavailable "The event head repository identity is invalid."
  [[ "$pull_number" =~ ^[1-9][0-9]*$ ]] || unavailable "The pull request number is invalid."
  baseline_sha="$event_base_sha"
  base_fallback_ref="refs/heads/$base_branch"
  head_fallback_ref="refs/pull/$pull_number/head"
fi

if [[ -n "${BASE_REF:-}" ]]; then
  baseline_sha="$(resolve_explicit_base)" || unavailable "The explicit base-ref could not be resolved to a commit."
fi

if [[ -z "$current_sha" ]]; then
  current_sha="$(git -c core.hooksPath=/dev/null -C "$WORKSPACE" rev-parse --verify 'HEAD^{commit}' 2>/dev/null)" ||
    unavailable "The current HEAD commit could not be resolved."
fi
is_sha "$current_sha" || unavailable "The current revision is not an immutable commit SHA."

if ! ensure_commit "$current_sha" "$head_fallback_ref"; then
  unavailable "The immutable current commit is absent and could not be fetched."
fi
if [[ -n "${BASELINE_INPUT_PATH:-}" ]]; then
  printf 'Using provided baseline snapshot with current=%s: %s\n' "$current_sha" "$BASELINE_INPUT_PATH"
else
  printf 'Resolved immutable comparison revisions: baseline=%s current=%s\n' "${baseline_sha:-unavailable}" "$current_sha"
fi

current_worktree="$comparison_temp/current"
if ! git -c core.hooksPath=/dev/null -C "$WORKSPACE" worktree add --quiet --detach "$current_worktree" "$current_sha"; then
  unavailable "The current revision could not be checked out in an isolated worktree."
fi

snapshot_arguments=()
[[ "${INCLUDE_GENERATED:-false}" == "true" ]] && snapshot_arguments+=(--include-generated)
[[ "${DETECT_DUPLICATES:-false}" == "true" ]] && snapshot_arguments+=(--detect-duplicates)

run_snapshot() {
  local source_root="$1"
  local output_path="$2"
  local revision="$3"
  local source_entry_path="$source_root/$ANALYSIS_RELATIVE_PATH"
  [[ -f "$source_entry_path" ]] || return 3
  local analysis_root="$comparison_temp/analysis-$revision"
  local state_root="$comparison_temp/state-$3"
  mkdir -p "$analysis_root" "$state_root/home" "$state_root/tmp" || return 1
  command -v tar >/dev/null 2>&1 || return 1
  tar --create --file - --directory "$source_root" --exclude='./.git' . |
    tar --extract --file - --directory "$analysis_root" || return 1
  local entry_path="$analysis_root/$ANALYSIS_RELATIVE_PATH"
  (
    cd "$analysis_root" || exit 1
    run_tool_safely "$state_root" analyze "$entry_path" "${snapshot_arguments[@]}" --snapshot --format json --output "$output_path"
  )
}

run_tool_safely() {
  local state_root="$1"
  shift
  mkdir -p "$state_root/home" "$state_root/tmp"
  local safe_environment=(
    env -i
    "PATH=$PATH"
    "HOME=$state_root/home"
    "TMPDIR=$state_root/tmp"
    "LANG=${LANG:-C.UTF-8}"
    "BaseIntermediateOutputPath=$state_root/intermediate/\$(MSBuildProjectName)/"
    "MSBuildProjectExtensionsPath=$state_root/intermediate/\$(MSBuildProjectName)/"
    "BaseOutputPath=$state_root/output/\$(MSBuildProjectName)/"
    "NUGET_PACKAGES=$state_root/packages"
    "DOTNET_CLI_TELEMETRY_OPTOUT=1"
    "DOTNET_NOLOGO=1"
  )
  [[ -n "${DOTNET_ROOT:-}" ]] && safe_environment+=("DOTNET_ROOT=$DOTNET_ROOT")
  [[ -n "${DOTNET_HOST_PATH:-}" ]] && safe_environment+=("DOTNET_HOST_PATH=$DOTNET_HOST_PATH")
  for test_name in \
    COMPLEXITY_ACTION_TEST_INVOCATIONS \
    COMPLEXITY_ACTION_TEST_COMPARISON_CLASSIFICATION \
    COMPLEXITY_ACTION_TEST_COMPARE_EXIT_CODE; do
    [[ -n "${!test_name:-}" ]] && safe_environment+=("$test_name=${!test_name}")
  done
  "${safe_environment[@]}" "$TOOL_COMMAND" "$@"
}

if [[ -n "$preserved_baseline_input" ]]; then
  if ! cp -- "$preserved_baseline_input" "$BASELINE_REPORT_PATH"; then
    failed "The provided baseline snapshot could not be preserved."
  fi
else
  [[ -n "$baseline_sha" ]] || unavailable "No baseline is available. Use a pull_request event, base-ref, or baseline-path."
  is_sha "$baseline_sha" || unavailable "The baseline revision is not an immutable commit SHA."
  if ! ensure_commit "$baseline_sha" "$base_fallback_ref"; then
    unavailable "The immutable baseline commit is absent and could not be fetched."
  fi
  baseline_worktree="$comparison_temp/baseline"
  if ! git -c core.hooksPath=/dev/null -C "$WORKSPACE" worktree add --quiet --detach "$baseline_worktree" "$baseline_sha"; then
    unavailable "The baseline revision could not be checked out in an isolated worktree."
  fi
  run_snapshot "$baseline_worktree" "$BASELINE_REPORT_PATH" baseline
  baseline_exit=$?
  if (( baseline_exit == 3 )); then
    unavailable "The analysis entry point does not exist at the baseline revision."
  elif (( baseline_exit != 0 )); then
    failed "The CLI could not generate the baseline snapshot."
  fi
fi

run_snapshot "$current_worktree" "$CURRENT_REPORT_PATH" current
current_exit=$?
if (( current_exit == 3 )); then
  unavailable "The analysis entry point does not exist at the current revision."
elif (( current_exit != 0 )); then
  failed "The CLI could not generate the current snapshot."
fi

set +e
run_tool_safely "$comparison_temp/state-compare-json" compare "$BASELINE_REPORT_PATH" "$CURRENT_REPORT_PATH" \
  --format json --output "$COMPARISON_REPORT_PATH" --fail-on-regression
comparison_exit=$?
set -e
if (( comparison_exit != 0 && comparison_exit != 2 )); then
  failed "The CLI could not compare the snapshots (exit code $comparison_exit)."
fi

regression_count="$(python3 "$ACTION_PATH/scripts/inspect-comparison.py" "$COMPARISON_REPORT_PATH")" ||
  failed "The CLI produced an invalid comparison report."
[[ "$regression_count" =~ ^[0-9]+$ ]] || failed "The comparison regression count is invalid."

set +e
run_tool_safely "$comparison_temp/state-compare-sarif" compare "$BASELINE_REPORT_PATH" "$CURRENT_REPORT_PATH" \
  --format sarif --output "$COMPARISON_SARIF_PATH" --fail-on-regression
sarif_exit=$?
set -e
if [[ "$sarif_exit" != "$comparison_exit" ]] ||
  ! python3 "$ACTION_PATH/scripts/validate-report.py" sarif "$COMPARISON_SARIF_PATH"; then
  failed "The CLI did not produce a valid comparison SARIF report with matching semantics."
fi

if (( comparison_exit == 2 )); then
  (( regression_count > 0 )) || failed "The CLI returned a regression exit code without a proven regression finding."
  printf '::warning title=Complexity regressions detected::%s proven regression(s) were reported.\n' "$regression_count"
  emit_result regressions-detected "$regression_count" 2
else
  (( regression_count == 0 )) || failed "The CLI reported regressions without returning its regression exit code."
  emit_result no-regressions 0 0
fi
