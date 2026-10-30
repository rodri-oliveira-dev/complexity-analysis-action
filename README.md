# Complexity Analysis Action

Reusable GitHub Action for deterministic complexity analysis of C# projects and
solutions. The Action installs and invokes the published
[`ComplexityAnalysis.Tool`](https://www.nuget.org/packages/ComplexityAnalysis.Tool)
CLI; it does not copy or reimplement the analysis engine.

> [!IMPORTANT]
> This is the Phase 2 prerelease. It supports `ubuntu-latest` only and has not been
> released or published to GitHub Marketplace. Use a reviewed full commit SHA
> during evaluation. Release aliases such as `@v1` do not exist yet.

## Requirements

- A GitHub-hosted or self-hosted Ubuntu runner with Bash, Python 3, and network
  access to NuGet.org. The Action installs the pinned .NET 10 SDK itself.
- A Git checkout containing a `.csproj`, `.sln`, or `.slnx` entry point. Git is
  required when baseline comparison is enabled.
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
          compare-with-base: "true"
          fail-on-regression: "true"

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
| `compare-with-base` | No | `false` | Opt in to automatic baseline generation. In a PR, uses the immutable event base and head SHAs. |
| `base-ref` | No | unset | Explicit commit or safe Git ref for automatic baseline generation. Requires `compare-with-base`; mutually exclusive with `baseline-path`. |
| `fail-on-regression` | No | `false` | Fail only when the CLI proves at least one regression. Requires a comparison source. |
| `baseline-path` | No | unset | Existing `complexity-snapshot/1.0` JSON inside the workspace. Supplying it enables comparison and replaces Git baseline generation. |
| `comparison-output` | No | `<output-directory>/comparison.json` | Workspace JSON path for comparison results. |

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
| `baseline-report-path` | Absolute path reserved for the preserved/generated `baseline.json`. |
| `current-report-path` | Absolute path reserved for the generated `current.json`. |
| `comparison-report-path` | Absolute path to `comparison.json`. |
| `regression-count` | Count of CLI findings classified exactly as `regression`; `0` when comparison does not complete. |
| `comparison-status` | `not-requested`, `no-regressions`, `regressions-detected`, `unavailable`, or `failed`. |

Both reports are generated before a configured quality-gate failure is applied.
The Job Summary shows the analyzed entry point, CLI version, configured
thresholds, results reported by the CLI, overall status, and report paths. To
retain the files after the job, upload either output with
`actions/upload-artifact` as shown above.

## Pull-request baselines

Comparison is opt-in. For a `pull_request` event, the Action reads the base
repository, base commit SHA, head repository, and head commit SHA from the event
payload. It verifies the identities, resolves only those immutable commits, and
fetches the exact missing objects (or the matching base/PR ref) for shallow and
fork checkouts. A fallback is accepted only when the expected SHA becomes
available; the Action never substitutes another commit.

The revisions are materialized in temporary detached worktrees, copied without
`.git`, and analyzed with identical snapshot options. The published CLI remains
the sole comparison engine and is invoked with `--fail-on-regression`. Successful
comparison creates:

- `baseline.json` — baseline `complexity-snapshot/1.0` report.
- `current.json` — current/head snapshot.
- `comparison.json` — CLI `complexity-comparison/1.0` report.
- `comparison.sarif` — local comparison SARIF (not uploaded automatically).

Supplying `baseline-path` copies that snapshot to `baseline.json`. Outside a PR,
automatic generation requires `base-ref`; the current revision is checked-out
`HEAD`. If an entry point is absent, a commit is inaccessible, or the CLI cannot
produce complete compatible report data, the status is `unavailable` or
`failed` and the Action fails without claiming “no regression.” Unknown or
incomparable complexity, added/removed members, and ambiguous identities stay
non-regressions according to the CLI and remain visible in `comparison.json`.

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

Absolute quality gates and baseline regressions are independent. The Phase 1
report retains thresholds and `fail-on-quality-gate`; comparison snapshots omit
thresholds and `fail-on-regression` applies only to proven CLI regression
findings. A project can exceed a threshold without adding a regression, or add
a regression while remaining below every threshold.

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

The Action rejects `pull_request_target`. Snapshot evaluation receives neither
the checkout's `.git` metadata nor the workflow environment: the CLI runs with
a minimal runtime allowlist and isolated HOME, temp, NuGet, and MSBuild state.
Keep permissions at `contents: read`, do not pass secrets through project
properties, and do not place credentials in checkout files. Project loading can
execute repository-controlled MSBuild imports and targets; process and network
sandboxing remain the runner owner's responsibility.

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
- Git refs use a conservative character set and resolve to commit SHAs before
  project evaluation. They are passed as arguments and never evaluated as code.

The CLI supports `.csproj`, `.sln`, and `.slnx` inputs and requires .NET 10.
Version `1.0.0` is the published package version exercised by the end-to-end
suite. Comparison currently assumes the configured entry-point path exists in
both revisions; an entry-point rename is unavailable rather than guessed.
Member/source-file renames, project additions/deletions, multiple target
frameworks, generated-code settings, and evidence compatibility are left to the
CLI snapshot matcher. The Action does not add PR comments, upload comparison
SARIF, infer alternate entry points, support non-Linux runners, or provide a
process/network sandbox.

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
- **Comparison unavailable:** inspect the logged immutable SHAs and confirm the
  checkout's `origin` can read the base repository. For custom history, provide
  `base-ref` or a valid snapshot through `baseline-path`.
- **Unknown/incomparable evidence did not fail:** expected; only CLI findings
  classified as `regression` can fail the regression gate.
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
bash tests/integration/test-comparison-scripts.sh
bash tests/integration/test-published-cli.sh
bash tests/integration/test-pr-regression-e2e.sh
```

The static script downloads exact actionlint, action-validator, and ShellCheck
versions and verifies their SHA-256 digests before use. Repository CI consumes
`uses: ./` and installs the published NuGet package for `.csproj`, `.sln`, and
`.slnx` entry points,
including paths containing spaces. It also asserts expected installation,
input, quality-gate, execution, and cancellation failures without masking an
unexpected result.
