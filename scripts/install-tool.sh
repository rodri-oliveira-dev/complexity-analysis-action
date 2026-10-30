#!/usr/bin/env bash

set -euo pipefail

fail() {
  printf '::error title=Complexity Analysis CLI installation failed::%s\n' "$1"
  exit 1
}

[[ -n "${RUNNER_TEMP:-}" ]] || fail "RUNNER_TEMP is not available."
[[ -f "${NUGET_CONFIG:-}" ]] || fail "The Action's NuGet configuration is unavailable."
tool_directory="$(mktemp -d "$RUNNER_TEMP/complexity-analysis-tool.XXXXXX")" ||
  fail "Unable to create the temporary tool directory."

printf 'Installing ComplexityAnalysis.Tool %s from NuGet.org...\n' "$TOOL_VERSION"
if ! dotnet tool install ComplexityAnalysis.Tool \
  --tool-path "$tool_directory" \
  --version "$TOOL_VERSION" \
  --configfile "$NUGET_CONFIG"; then
  fail "Could not install ComplexityAnalysis.Tool version '$TOOL_VERSION'. Confirm that the exact version is published on NuGet.org."
fi

tool_command="$tool_directory/complexity-analysis"
[[ -x "$tool_command" ]] || fail "The installed package did not provide the complexity-analysis command."

installed_version="$($tool_command --version)" || fail "Unable to read the installed CLI version."
[[ "$installed_version" == "$TOOL_VERSION" ]] ||
  fail "Installed CLI version '$installed_version' does not match requested version '$TOOL_VERSION'."

printf 'tool-directory=%s\n' "$tool_directory" >> "$GITHUB_OUTPUT"
printf 'Installed ComplexityAnalysis.Tool %s.\n' "$installed_version"
