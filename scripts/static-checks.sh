#!/usr/bin/env bash

set -euo pipefail

readonly actionlint_version="1.7.7"
readonly actionlint_sha256="023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757"
readonly action_validator_version="0.9.0"
readonly action_validator_sha256="9f42f94fca5b8d04c13bccfbb331104b37a9250650d89ae58dc888d46206f9b9"
readonly shellcheck_version="0.10.0"
readonly shellcheck_sha256="6c881ab0698e4e6ea235245f22832860544f17ba386442fe7e9d629f8cbedf87"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tool_root="$(mktemp -d "${RUNNER_TEMP:-/tmp}/complexity-analysis-validation.XXXXXX")"
trap 'rm -rf -- "$tool_root"' EXIT

download_checked() {
  local url="$1"
  local destination="$2"
  local expected_sha="$3"
  curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
    "$url" --output "$destination"
  printf '%s  %s\n' "$expected_sha" "$destination" | sha256sum --check --status
}

actionlint_archive="$tool_root/actionlint.tar.gz"
download_checked \
  "https://github.com/rhysd/actionlint/releases/download/v${actionlint_version}/actionlint_${actionlint_version}_linux_amd64.tar.gz" \
  "$actionlint_archive" "$actionlint_sha256"
tar --extract --gzip --file "$actionlint_archive" --directory "$tool_root" actionlint

action_validator="$tool_root/action-validator"
download_checked \
  "https://github.com/mpalmer/action-validator/releases/download/v${action_validator_version}/action-validator_linux_amd64" \
  "$action_validator" "$action_validator_sha256"
chmod +x "$action_validator"

shellcheck_archive="$tool_root/shellcheck.tar.xz"
download_checked \
  "https://github.com/koalaman/shellcheck/releases/download/v${shellcheck_version}/shellcheck-v${shellcheck_version}.linux.x86_64.tar.xz" \
  "$shellcheck_archive" "$shellcheck_sha256"
tar --extract --xz --file "$shellcheck_archive" --directory "$tool_root"

cd "$repo_root"
bash -n scripts/*.sh tests/integration/*.sh
"$tool_root/shellcheck-v${shellcheck_version}/shellcheck" scripts/*.sh tests/integration/*.sh
python3 -m compileall -q scripts tests
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/static/check-action-pins.py action.yml .github/workflows/*.yml examples/*.yml
"$tool_root/actionlint" -color
"$tool_root/actionlint" -color examples/*.yml
"$action_validator" action.yml
"$action_validator" publish-pr-report/action.yml
"$action_validator" .github/workflows/ci.yml
"$action_validator" .github/workflows/e2e.yml
"$action_validator" .github/workflows/codeql.yml
"$action_validator" .github/workflows/release-readiness.yml
"$action_validator" examples/consumer-workflow.yml
"$action_validator" examples/secure-pr-analysis.yml
"$action_validator" examples/secure-pr-publish.yml
git diff --check
