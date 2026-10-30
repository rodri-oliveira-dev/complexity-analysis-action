#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
test_root="$(mktemp -d "${RUNNER_TEMP:-/tmp}/complexity-pr-reporting.XXXXXX")"
trap 'rm -rf -- "$test_root"' EXIT
mkdir -p "$test_root/reports"

base_sha="$(printf 'a%.0s' {1..40})"
head_sha="$(printf 'b%.0s' {1..40})"
event_path="$test_root/event.json"
printf '{"pull_request":{"number":7,"base":{"sha":"%s","repo":{"full_name":"owner/repository"}},"head":{"sha":"%s","repo":{"full_name":"fork/repository"}}}}\n' \
  "$base_sha" "$head_sha" > "$event_path"

comparison_path="$test_root/reports/comparison.json"
printf '%s\n' '{"SchemaVersion":"complexity-comparison/1.0","BaselineSchemaVersion":"complexity-snapshot/1.0","CurrentSchemaVersion":"complexity-snapshot/1.0","Findings":[{"StableId":"M:Sample.Work()","Classification":"regression","Reason":"The current estimate grows faster than the baseline.","Before":"O(n)","After":"O(n^2)","Location":{"FilePath":"src/Sample.cs","StartLine":12},"Evidence":{"Steps":[{"Kind":"loop","Estimate":{"Status":"known"}}]}}]}' > "$comparison_path"
for report in analysis.json analysis.sarif baseline.json current.json; do
  printf '{}\n' > "$test_root/reports/$report"
done

report_path="$test_root/reports/pr-report.json"
env \
  GITHUB_EVENT_PATH="$event_path" GITHUB_EVENT_NAME=pull_request GITHUB_REPOSITORY=owner/repository \
  GITHUB_RUN_ID=123 GITHUB_WORKFLOW='Complexity PR analysis' WORKSPACE="$test_root" \
  ANALYSIS_RELATIVE_PATH=src/Sample.slnx REPORT_PATH="$test_root/reports/analysis.json" \
  SARIF_PATH="$test_root/reports/analysis.sarif" BASELINE_REPORT_PATH="$test_root/reports/baseline.json" \
  CURRENT_REPORT_PATH="$test_root/reports/current.json" COMPARISON_REPORT_PATH="$comparison_path" \
  PR_REPORT_PATH="$report_path" COMPARISON_STATUS=regressions-detected REGRESSION_COUNT=1 \
  QUALITY_GATE_STATUS=passed BASE_REVISION_KIND=commit BASE_REVISION="$base_sha" \
  python3 "$repo_root/scripts/build-pr-report.py"

PYTHONPATH="$repo_root/scripts" python3 - "$report_path" "$head_sha" <<'PY'
import sys
from pathlib import Path
from pr_reporting import MARKER, load_json, render_comment, validate_envelope

report = validate_envelope(
    load_json(Path(sys.argv[1])), repository="owner/repository", head_sha=sys.argv[2],
    pr_number=7, run_id="123", workflow_name="Complexity PR analysis"
)
comment = render_comment(report)
assert comment.count(MARKER) == 1
assert "M:Sample.Work()" in comment
assert "O(n^2)" in comment
assert report["PullRequest"]["IsFork"] is True
PY

# Publication is opt-in: generation never needs or receives a token.
test -s "$report_path"
printf 'Pull-request reporting integration test passed.\n'
