#!/usr/bin/env bash

set -euo pipefail

tool_command="$TOOL_DIRECTORY/complexity-analysis"
common_arguments=(analyze "$ANALYSIS_PATH")

if [[ "$INCLUDE_GENERATED" == "true" ]]; then
  common_arguments+=(--include-generated)
fi

if [[ "$DETECT_DUPLICATES" == "true" ]]; then
  common_arguments+=(--detect-duplicates)
fi

append_value_option() {
  local option="$1"
  local value="$2"
  if [[ -n "$value" ]]; then
    common_arguments+=("$option" "$value")
  fi
}

append_value_option --max-complexity "$MAX_COMPLEXITY"
append_value_option --max-cyclomatic-complexity "$MAX_CYCLOMATIC_COMPLEXITY"
append_value_option --max-cognitive-complexity "$MAX_COGNITIVE_COMPLEXITY"
append_value_option --max-nesting-depth "$MAX_NESTING_DEPTH"
append_value_option --max-method-nloc "$MAX_METHOD_NLOC"
append_value_option --max-duplicate-rate "$MAX_DUPLICATE_RATE"

rm -f -- "$REPORT_PATH" "$SARIF_PATH"

run_cli() {
  local format="$1"
  local output_path="$2"
  local arguments=("${common_arguments[@]}" --format "$format" --output "$output_path")
  "$tool_command" "${arguments[@]}"
}

validate_report() {
  local format="$1"
  local candidate_path="$2"
  python3 "$(dirname "$0")/validate-report.py" "$format" "$candidate_path"
}

printf 'Running Complexity Analysis JSON report...\n'
set +e
run_cli json "$REPORT_PATH"
json_exit_code=$?
set -e

json_valid=false
if [[ -s "$REPORT_PATH" ]] && validate_report json "$REPORT_PATH"; then
  json_valid=true
fi

sarif_exit_code=""
sarif_valid=false
if (( json_exit_code == 0 || json_exit_code == 2 )); then
  printf 'Running Complexity Analysis SARIF report...\n'
  set +e
  run_cli sarif "$SARIF_PATH"
  sarif_exit_code=$?
  set -e

  if [[ -s "$SARIF_PATH" ]] && validate_report sarif "$SARIF_PATH"; then
    sarif_valid=true
  fi
fi

effective_exit_code=$json_exit_code
analysis_status=failed
quality_gate_status=unknown

if (( json_exit_code == 0 || json_exit_code == 2 )); then
  if [[ "$json_valid" != "true" ]]; then
    printf '::error title=Complexity Analysis report error::The CLI did not produce a valid JSON report.\n'
    effective_exit_code=1
  elif [[ "$sarif_exit_code" != "$json_exit_code" ]]; then
    printf '::error title=Complexity Analysis report error::JSON and SARIF executions returned different exit codes (%s and %s).\n' "$json_exit_code" "${sarif_exit_code:-not-run}"
    effective_exit_code=1
  elif [[ "$sarif_valid" != "true" ]]; then
    printf '::error title=Complexity Analysis report error::The CLI did not produce a valid SARIF 2.1.0 report.\n'
    effective_exit_code=1
  else
    analysis_status=success
    if [[ "$HAS_THRESHOLDS" == "true" ]]; then
      if (( json_exit_code == 2 )); then
        quality_gate_status=failed
        printf '::warning title=Complexity Analysis quality gate failed::At least one configured threshold was exceeded. Reports were generated successfully.\n'
      else
        quality_gate_status=passed
      fi
    else
      quality_gate_status=not-configured
    fi
  fi
elif (( json_exit_code == 130 )); then
  analysis_status=canceled
  printf '::error title=Complexity Analysis canceled::The CLI exited with code 130.\n'
else
  printf '::error title=Complexity Analysis failed::The CLI exited with code %d. Review the preceding CLI output for details.\n' "$json_exit_code"
fi

{
  printf 'analysis-status=%s\n' "$analysis_status"
  printf 'quality-gate-status=%s\n' "$quality_gate_status"
  printf 'analysis-exit-code=%s\n' "$effective_exit_code"
  printf 'json-valid=%s\n' "$json_valid"
  printf 'sarif-valid=%s\n' "$sarif_valid"
} >> "$GITHUB_OUTPUT"

if [[ "$json_valid" == "true" ]]; then
  printf 'Complexity Analysis JSON report: %s\n' "$REPORT_PATH"
fi
if [[ "$sarif_valid" == "true" ]]; then
  printf 'Complexity Analysis SARIF report: %s\n' "$SARIF_PATH"
fi
