#!/usr/bin/env bash

set -euo pipefail

if [[ -n "${GITHUB_TOKEN:-}" || -n "${COMPLEXITY_ACTION_TEST_SECRET:-}" ]]; then
  printf 'The analysis process received a workflow secret.\n' >&2
  exit 99
fi

if [[ "${1:-}" == "--version" ]]; then
  printf '1.0.0\n'
  exit 0
fi

command="${1:-}"
shift || true

if [[ "$command" == "analyze" ]]; then
  analysis_path="${1:-}"
  shift
  format=""
  output=""
  detect_duplicates=false
  snapshot=false
  while (($#)); do
    case "$1" in
      --format) format="$2"; shift 2 ;;
      --output) output="$2"; shift 2 ;;
      --detect-duplicates) detect_duplicates=true; shift ;;
      --include-generated) shift ;;
      --snapshot) snapshot=true; shift ;;
      --max-*) shift 2 ;;
      *) exit 1 ;;
    esac
  done

  printf 'analyze|%s|%s|%s|%s\n' "$analysis_path" "$format" "$detect_duplicates" "$snapshot" >> "${COMPLEXITY_ACTION_TEST_INVOCATIONS:?}"
  if [[ "$format" == "json" && "$snapshot" == "true" ]]; then
    printf '{"SchemaVersion":"complexity-snapshot/1.0","Deterministic":true,"EntryPoint":"Sample.csproj","Projects":[],"QualityGates":[]}\n' > "$output"
  elif [[ "$format" == "json" ]]; then
    printf '{"SchemaVersion":"1.0","EntryPoint":"%s","Projects":[{"Name":"Sample","Path":"Sample.csproj","Files":[]}],"QualityGates":[]}\n' \
      "$analysis_path" > "$output"
  elif [[ "$format" == "sarif" ]]; then
    printf '{"version":"2.1.0","runs":[{"tool":{"driver":{"name":"ComplexityAnalysis.Tool"}},"results":[]}]}\n' > "$output"
  else
    exit 1
  fi
  exit "${COMPLEXITY_ACTION_TEST_EXIT_CODE:-0}"
fi

if [[ "$command" == "compare" ]]; then
  baseline="${1:-}"
  current="${2:-}"
  shift 2
  format=""
  output=""
  fail_on_regression=false
  while (($#)); do
    case "$1" in
      --format) format="$2"; shift 2 ;;
      --output) output="$2"; shift 2 ;;
      --fail-on-regression) fail_on_regression=true; shift ;;
      *) exit 1 ;;
    esac
  done
  classification="${COMPLEXITY_ACTION_TEST_COMPARISON_CLASSIFICATION:-equivalent}"
  printf 'compare|%s|%s|%s|%s\n' "$baseline" "$current" "$format" "$classification" >> "${COMPLEXITY_ACTION_TEST_INVOCATIONS:?}"
  if [[ "${COMPLEXITY_ACTION_TEST_COMPARE_EXIT_CODE:-}" =~ ^[0-9]+$ ]]; then
    exit "$COMPLEXITY_ACTION_TEST_COMPARE_EXIT_CODE"
  fi
  if [[ "$format" == "json" ]]; then
    printf '{"SchemaVersion":"complexity-comparison/1.0","BaselineSchemaVersion":"complexity-snapshot/1.0","CurrentSchemaVersion":"complexity-snapshot/1.0","Findings":[{"StableId":"M:Sample.Work()","Classification":"%s","Severity":"note","Reason":"controlled test finding","Before":"O(n)","After":"O(n^2)","Location":{"FilePath":"Sample.cs","StartLine":10},"Evidence":{"Steps":[{"Kind":"loop","Estimate":{"Status":"known"}}]}}]}\n' \
      "$classification" > "$output"
  elif [[ "$format" == "sarif" ]]; then
    printf '{"version":"2.1.0","runs":[{"tool":{"driver":{"name":"ComplexityAnalysis.Tool"}},"results":[]}]}\n' > "$output"
  else
    exit 1
  fi
  if [[ "$classification" == "regression" && "$fail_on_regression" == "true" ]]; then
    exit 2
  fi
  exit 0
fi

exit 1
