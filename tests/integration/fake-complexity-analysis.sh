#!/usr/bin/env bash

set -euo pipefail

if [[ "${1:-}" == "--version" ]]; then
  printf '1.0.0\n'
  exit 0
fi

[[ "${1:-}" == "analyze" ]] || exit 1
shift
analysis_path="${1:-}"
shift
format=""
output=""
detect_duplicates=false
while (($#)); do
  case "$1" in
    --format) format="$2"; shift 2 ;;
    --output) output="$2"; shift 2 ;;
    --detect-duplicates) detect_duplicates=true; shift ;;
    --include-generated) shift ;;
    --max-*) shift 2 ;;
    *) exit 1 ;;
  esac
done

printf '%s|%s|%s\n' "$analysis_path" "$format" "$detect_duplicates" >> "${FAKE_INVOCATIONS:?}"
if [[ "$format" == "json" ]]; then
  printf '{"SchemaVersion":"1.0","EntryPoint":"%s","Projects":[{"Name":"Sample","Path":"Sample.csproj","Files":[]}],"QualityGates":[]}\n' \
    "$analysis_path" > "$output"
elif [[ "$format" == "sarif" ]]; then
  printf '{"version":"2.1.0","runs":[{"tool":{"driver":{"name":"ComplexityAnalysis.Tool"}},"results":[]}]}\n' > "$output"
else
  exit 1
fi

exit "${FAKE_EXIT_CODE:-0}"
