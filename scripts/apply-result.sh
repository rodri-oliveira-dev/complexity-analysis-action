#!/usr/bin/env bash

set -euo pipefail

case "$ANALYSIS_EXIT_CODE" in
  0)
    ;;
  1)
    printf '::error title=Complexity Analysis failed::The CLI reported an execution or configuration failure.\n'
    exit 1
    ;;
  2)
    ;;
  130)
    printf '::error title=Complexity Analysis canceled::The CLI reported cancellation.\n'
    exit 130
    ;;
  *)
    printf '::error title=Complexity Analysis failed::No recognized CLI result was available.\n'
    exit 1
    ;;
esac

if [[ "$UPLOAD_SARIF" == "true" ]]; then
  if [[ "$SARIF_VALIDATION_OUTCOME" != "success" ]]; then
    printf '::error title=Complexity Analysis SARIF upload blocked::The SARIF report did not pass pre-upload validation.\n'
    exit 1
  fi
  if [[ "$SARIF_UPLOAD_OUTCOME" != "success" ]]; then
    printf '::error title=Complexity Analysis SARIF upload failed::The requested Code Scanning upload did not succeed.\n'
    exit 1
  fi
fi

if [[ "$ANALYSIS_EXIT_CODE" == "2" ]]; then
  if [[ "$FAIL_ON_QUALITY_GATE" == "true" ]]; then
    printf '::error title=Complexity Analysis quality gate failed::At least one configured threshold was exceeded.\n'
    exit 2
  fi
  printf 'Quality-gate violations are allowed by fail-on-quality-gate=false.\n'
fi
