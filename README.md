# Complexity Analysis Action

Reusable GitHub Action for deterministic complexity analysis of C# projects and
solutions. The Action installs and invokes the published
[`ComplexityAnalysis.Tool`](https://www.nuget.org/packages/ComplexityAnalysis.Tool)
CLI; it does not copy or reimplement the analysis engine.

> [!IMPORTANT]
> This is the Phase 1 MVP. It supports `ubuntu-latest` only and has not been
> released or published to GitHub Marketplace. Use a reviewed full commit SHA
> during evaluation. Release aliases such as `@v1` do not exist yet.

## Requirements

- A GitHub-hosted or self-hosted Ubuntu runner with Bash, Python 3, and network
  access to NuGet.org. The Action installs the pinned .NET 10 SDK itself.
- A `.csproj`, `.sln`, or `.slnx` entry point inside the checked-out workspace.
- `contents: read` is the only workflow permission required for local reports.
  SARIF upload additionally requires `security-events: write`.

## Usage

```yaml
name: Complexity Analysis

on:
  pull_request:

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      # actions/checkout v6.0.2
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd

      # Replace this placeholder with a reviewed full commit SHA.
      - id: complexity
        uses: rodri-oliveira-dev/complexity-analysis-action@0000000000000000000000000000000000000000
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

      # actions/upload-artifact v5.0.0
      - uses: actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4
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

Never use `pull_request_target` to check out and analyze pull-request code. The
CLI loads project/solution content through MSBuild, so repository-controlled
project and target files must be treated as untrusted executable input. Run with
a read-only token, no secrets, and no write-capable credentials. The Action
isolates normal MSBuild, build, and NuGet state under `RUNNER_TEMP`, but that is
not a sandbox for malicious project content.

## Behavior and safety

- The Action sets up .NET 10 and installs the exact requested CLI version from
  an explicit NuGet.org-only configuration into an isolated temporary tool
  directory.
- Input and output paths must resolve inside `GITHUB_WORKSPACE`.
- Inputs are passed through environment variables and arguments are built as a
  Bash array. Input text is never evaluated as a shell command.
- Analysis runs against an isolated runner-temporary copy of the workspace;
  normal MSBuild intermediate, output, and NuGet package state does not modify
  the checkout. The configured reports are the only expected workspace writes.
- Missing paths, unsupported extensions and runners, malformed versions,
  installation errors, and CLI failures produce explicit workflow errors.
- Reports are generated by the CLI as JSON and SARIF 2.1.0; the Action does not
  reproduce complexity calculations or quality-gate evaluation.

The CLI supports `.csproj`, `.sln`, and `.slnx` inputs and requires .NET 10.
Version `1.0.0` is the published package version exercised by the end-to-end
suite. The MVP intentionally does not include trend analysis, baselines,
annotations beyond the CLI's reports, multi-platform runners, release
automation, Marketplace publication, or website changes.

## Troubleshooting

- **Unsupported runner:** use Ubuntu. Windows and macOS are not supported by the
  MVP.
- **Path rejected:** provide a file inside `GITHUB_WORKSPACE`; paths outside the
  checkout, the workspace root as an output directory, and `.git` output paths
  are rejected.
- **CLI installation failed:** confirm the exact `tool-version` exists on
  NuGet.org and that the runner can reach `https://api.nuget.org`.
- **Quality gate failed:** inspect the JSON report and job summary. Set
  `fail-on-quality-gate: "false"` only when violations should be reported without
  failing the job.
- **SARIF upload failed:** verify `security-events: write`, repository Code
  Scanning availability, and fork restrictions. Local JSON and SARIF files are
  still retained for later artifact upload.
- **Reports are missing after the job:** outputs are paths on the runner; add an
  artifact upload step if they must be retained.

## Development validation

From a Bash environment on Ubuntu:

```bash
bash scripts/static-checks.sh
bash tests/integration/test-action-scripts.sh
bash tests/integration/test-published-cli.sh
```

The static script downloads exact actionlint, action-validator, and ShellCheck
versions and verifies their SHA-256 digests before use. Repository CI consumes
`uses: ./` and installs the published NuGet package for `.csproj`, `.sln`, and
`.slnx` entry points,
including paths containing spaces. It also asserts expected installation,
input, quality-gate, execution, and cancellation failures without masking an
unexpected result.
