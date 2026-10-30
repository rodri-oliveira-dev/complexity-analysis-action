# Complexity Analysis Action

Reusable GitHub Action for deterministic complexity analysis of C# projects and
solutions. The Action installs and invokes the published
[`ComplexityAnalysis.Tool`](https://www.nuget.org/packages/ComplexityAnalysis.Tool)
CLI; it does not copy or reimplement the analysis engine.

> [!IMPORTANT]
> The initial version supports `ubuntu-latest` only. The `@v1` reference shown
> below is reserved for a future release and does not exist yet. Until that
> release is created, use a commit SHA or a development branch only in controlled
> testing.

## Usage

```yaml
name: Complexity Analysis

on:
  pull_request:

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      # Future release reference: v1 has not been published yet.
      - id: complexity
        uses: rodri-oliveira-dev/complexity-analysis-action@v1
        with:
          path: My Solution.slnx
          tool-version: 1.0.0
          output-directory: artifacts/complexity-analysis
          include-generated: "false"
          detect-duplicates: "true"
          max-complexity: n_log_n
          max-cyclomatic-complexity: "15"
          max-cognitive-complexity: "20"
          max-nesting-depth: "4"
          max-method-nloc: "80"
          max-duplicate-rate: "5"

      - uses: actions/upload-artifact@v5
        with:
          name: complexity-analysis-report
          path: ${{ steps.complexity.outputs.report-path }}
```

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `path` | Yes | - | Workspace-relative or absolute workspace path to a `.csproj`, `.sln`, or `.slnx` file. |
| `tool-version` | No | `1.0.0` | Exact published `ComplexityAnalysis.Tool` version. Floating versions are rejected. |
| `output-directory` | No | `complexity-analysis-reports` | Workspace directory for JSON and SARIF reports. |
| `include-generated` | No | `false` | Passes `--include-generated` when `true`. |
| `detect-duplicates` | No | `false` | Passes `--detect-duplicates` when `true`. |
| `max-complexity` | No | unset | Maximum Big-O classification accepted by the CLI. |
| `max-cyclomatic-complexity` | No | unset | Positive integer maximum per member. |
| `max-cognitive-complexity` | No | unset | Non-negative integer maximum per member. |
| `max-nesting-depth` | No | unset | Non-negative integer maximum per member. |
| `max-method-nloc` | No | unset | Positive integer maximum per member. |
| `max-duplicate-rate` | No | unset | Non-negative duplicate percentage; also enables duplicate detection. |
| `fail-on-quality-gate` | No | `true` | Return a failing Action result for CLI exit code `2`. Has no effect when no gate is configured. |
| `upload-sarif` | No | `false` | Validate and upload SARIF to GitHub Code Scanning. |

Boolean inputs accept only the lowercase strings `true` and `false`.
Thresholds are never enabled implicitly. Supported Big-O values are `constant`,
`log_n`, `linear`/`n`, `n_log_n`, `quadratic`/`n2`, `cubic`/`n3`,
`exponential`, and `factorial`.

## Outputs

| Output | Description |
| --- | --- |
| `report-path` | Absolute path to `complexity-analysis-report.json`. |
| `sarif-path` | Absolute path to `complexity-analysis-report.sarif`. |
| `analysis-status` | CLI execution result: `success`, `failed`, or `canceled`. A quality-gate violation is still a successful analysis. |
| `quality-gate-status` | `not-configured`, `passed`, `failed`, or `unknown`. |
| `tool-version` | Exact CLI package version used. |

Both reports are generated before a configured quality-gate failure is applied.
The Job Summary shows the analyzed entry point, CLI version, configured
thresholds, results reported by the CLI, overall status, and report paths. To
retain the files after the job, upload either output with
`actions/upload-artifact` as shown above.

## Quality-gate behavior

The Action preserves the CLI exit-code contract and does not evaluate metric
thresholds itself:

| CLI exit code | Meaning | Action behavior |
| --- | --- | --- |
| `0` | Analysis and configured gates succeeded. | Succeeds. |
| `1` | Execution or configuration failure. | Fails and reports the CLI error. |
| `2` | At least one configured gate failed. | Fails by default; succeeds with `fail-on-quality-gate: "false"`. Reports remain available. |
| `130` | Analysis canceled. | Stops with exit code `130`. |

High complexity alone does not fail the Action. The CLI can return `2` only
when at least one threshold was explicitly configured.

## Optional Code Scanning upload

SARIF upload is disabled by default. Enable it with `upload-sarif: "true"` and
grant the job only the permissions it needs:

```yaml
permissions:
  contents: read
  security-events: write
```

Private repositories may also require `actions: read` for the CodeQL upload
integration. Add it only when GitHub reports that requirement for the target
repository.

The Action validates SARIF 2.1.0 structure, repository-relative file locations,
and GitHub's 10 MB file limit before invoking the official
[`github/codeql-action/upload-sarif@v4`](https://github.com/github/codeql-action/tree/main/upload-sarif)
integration. The upload can still be
rejected when Code Scanning is unavailable for the repository, GitHub Code
Security is not enabled where required, or the workflow token lacks
`security-events: write`. The Action reports these cases as failures and keeps
the local reports available. See GitHub's
[SARIF upload documentation](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file)
for repository availability and ingestion limits.

For pull requests from forks, GitHub may restrict write permissions granted to
`GITHUB_TOKEN`; keep `upload-sarif` disabled for an untrusted fork workflow or
perform the upload in an appropriately secured workflow.

## Behavior and safety

- The Action sets up .NET 10 and installs the exact requested CLI version from
  an explicit NuGet.org-only configuration into an isolated temporary tool
  directory.
- Input and output paths must resolve inside `GITHUB_WORKSPACE`.
- Inputs are passed through environment variables and arguments are built as a
  Bash array. Input text is never evaluated as a shell command.
- Missing paths, unsupported extensions and runners, malformed versions,
  installation errors, and CLI failures produce explicit workflow errors.
- Reports are generated by the CLI as JSON and SARIF 2.1.0; the Action does not
  reproduce complexity calculations or quality-gate evaluation.

The CLI supports `.csproj`, `.sln`, and `.slnx` inputs and requires .NET 10.
Version `1.0.0` is the first public package version used by this Action.

## Development validation

From a Bash environment on Ubuntu:

```bash
bash -n scripts/*.sh
shellcheck scripts/*.sh
python3 -m compileall -q scripts
actionlint
```

The repository CI exercises the local Action against sample `.csproj`, `.sln`,
and `.slnx` entry points, including paths containing spaces.
