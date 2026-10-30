# Complexity Analysis Action

[![GitHub Action](https://img.shields.io/badge/GitHub-Action-2088FF?logo=githubactions&logoColor=white)](action.yml)

English | [Português (Brasil)](README.pt-BR.md)

**Get started:** [Add to a workflow](#quick-start) · [Examples](examples/) · [Release v1.0.0](https://github.com/rodri-oliveira-dev/complexity-analysis-action/releases/tag/v1.0.0) · [Marketplace verification](docs/marketplace.md)

Reusable GitHub Action for deterministic complexity analysis of C# projects and
solutions. The Action installs and invokes the published
[`ComplexityAnalysis.Tool`](https://www.nuget.org/packages/ComplexityAnalysis.Tool)
CLI; it does not copy or reimplement the analysis engine.
The CLI and analyzer are maintained in the
[`complexity-analyzers`](https://github.com/rodri-oliveira-dev/complexity-analyzers)
repository.

The Action uses independent Semantic Versioning. Its first stable release,
[`v1.0.0`](https://github.com/rodri-oliveira-dev/complexity-analysis-action/releases/tag/v1.0.0), was published on 2026-10-30;
the pinned CLI dependency is `ComplexityAnalysis.Tool` 1.0.1.

> [!IMPORTANT]
> `v1.0.0` is published and supports Ubuntu runners only. The optional moving
> `@v1` compatibility alias has not been created yet. Pin the approved release
> commit SHA for reproducibility; verify Marketplace listing availability
> separately from GitHub Release publication.

## Overview

Complexity Analysis helps .NET teams analyze C# complexity in CI pipelines,
enforce explicit quality gates, compare changes in pull requests, generate JSON
and SARIF reports, detect proven regressions, and review validated results in
GitHub. It uses structural metrics and estimated algorithmic complexity. It is
not a runtime benchmark, automatic performance optimizer, or precise predictor
of execution time.

## Quick start

Add `.github/workflows/complexity-analysis.yml` to the repository you want to
analyze. This example pins the published `v1.0.0` release commit. Replace
`MySolution.slnx` with your actual project or solution path.

```yaml
name: Complexity Analysis

on:
  pull_request:

permissions:
  contents: read

jobs:
  complexity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          persist-credentials: false
      - name: Analyze C# complexity
        uses: rodri-oliveira-dev/complexity-analysis-action@2d807ef29ca03c685d224543a135d8c30dfe2c67
        with:
          path: MySolution.slnx
```

**Version choices:** the published `@v1.0.0` tag is available as a convenient
stable reference, or you can pin the reviewed 40-character SHA above for stronger
reproducibility. The moving `@v1` alias does not exist yet; do not use it until
it has been created and verified. A GitHub Release does not itself prove that a
[Marketplace listing](docs/marketplace.md) is publicly visible.

Validated workflow examples:

- [Basic analysis](examples/basic-analysis.yml)
- [Configurable quality gates](examples/quality-gates.yml)
- [Non-blocking analysis](examples/non-blocking-analysis.yml)
- [SARIF upload](examples/sarif-upload.yml)
- [PR regression analysis](examples/secure-pr-analysis.yml)
- [Isolated fork PR feedback](examples/secure-pr-publish.yml)
- [Complete consumer workflow](examples/consumer-workflow.yml)

## Requirements

- A GitHub-hosted or self-hosted Ubuntu runner with Bash, Python 3, and network
  access to NuGet.org. The Action installs the pinned .NET 10 SDK itself.
- A Git checkout containing a `.csproj`, `.sln`, or `.slnx` entry point. Git is
  required when baseline comparison is enabled.
- `contents: read` is the only workflow permission required for local reports
  and regression checks. SARIF upload additionally requires
  `security-events: write`; direct PR comments additionally require
  `pull-requests: write`.

## Complete example

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
      # actions/checkout v7.0.1
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          persist-credentials: false

      # Pin to the reviewed v1.0.0 release commit.
      - id: complexity
        uses: rodri-oliveira-dev/complexity-analysis-action@2d807ef29ca03c685d224543a135d8c30dfe2c67
        with:
          path: My Solution.slnx
          tool-version: 1.0.1
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
          comment-on-pr: "false"

      # actions/upload-artifact v7.0.2
      - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9
        with:
          name: complexity-analysis-report
          path: ${{ steps.complexity.outputs.report-path }}
```

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `path` | Yes | - | Workspace-relative or absolute workspace path to a `.csproj`, `.sln`, or `.slnx` file. |
| `tool-version` | No | `1.0.1` | Exact published `ComplexityAnalysis.Tool` version. Floating versions are rejected. |
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
| `comment-on-pr` | No | `false` | Create or update one bot-authored PR report after a completed comparison. Requires a `pull_request` event and `pull-requests: write`. |

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
| `pr-report-path` | Absolute path reserved for validated `pr-report.json`; generated for completed PR comparisons even when commenting is disabled. |

Reports are generated before a configured quality-gate or regression failure is
applied. The Job Summary shows base/head revisions, proven regressions,
improvements, reliably equivalent members, comparison limitations,
quality-gate state, overall status, and report paths whether or not commenting
is enabled. To
retain the files after the job, upload either output with
`actions/upload-artifact` as shown above.

## Reporting modes

The capabilities are independently opt-in:

| Mode | Configuration | Required permissions | Result |
| --- | --- | --- | --- |
| Analysis only | Defaults, optionally with quality gates | `contents: read` | JSON, SARIF, and Job Summary; no comment. |
| Regression check | `compare-with-base: "true"`, optionally `fail-on-regression: "true"` | `contents: read` | Snapshots, comparison reports, summary, and optional failure; no write permission. |
| Direct PR feedback | Comparison plus `comment-on-pr: "true"` | `contents: read`, `pull-requests: write` | The same reports plus one idempotently updated comment. |
| Isolated fork feedback | Read-only analysis workflow plus `workflow_run` publisher | Analysis: `contents: read`; publisher: `actions: read`, `pull-requests: write` | The publisher consumes only the validated report artifact and never checks out or executes PR code. |

### Direct PR comment

Use direct comments for trusted same-repository PRs. Users who do not request a
comment do not need `pull-requests: write`.

```yaml
permissions:
  contents: read
  pull-requests: write

steps:
  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
    with:
      persist-credentials: false
  - uses: rodri-oliveira-dev/complexity-analysis-action@2d807ef29ca03c685d224543a135d8c30dfe2c67
    with:
      path: MySolution.slnx
      compare-with-base: "true"
      fail-on-regression: "false"
      comment-on-pr: "true"
```

The Markdown starts with a stable hidden marker. Publication uses only
`github.token`, paginates the PR comments, and updates only a marked comment owned by
the canonical `github-actions[bot]` identity. A copied marker in another user or
bot's comment is ignored. The comment displays at most ten regressions and points to the
workflow run and available report paths; the full deterministic result remains
in `comparison.json`. Repeated runs update the same comment instead of creating
notification spam.

Only a completed, validated comparison is published as findings. Execution,
configuration, metadata-validation, and API failures are emitted as workflow
errors or warnings and remain visibly separate from regression counts; the
Action never turns a missing report into "no regressions."

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
Reports identify the resolved commit actually used by `base-ref`. When
`baseline-path` is supplied, the comparison base is labeled "Provided snapshot"
instead of implying that the snapshot came from the PR event's base commit.

### Secure publication for fork PRs

Fork `pull_request` workflows normally receive a read-only token, so direct
commenting reports a warning and leaves `pr-report.json` available. Do not grant
write permissions or secrets to that analysis job. For comments on fork PRs,
use the two-workflow pattern in
[`examples/secure-pr-analysis.yml`](examples/secure-pr-analysis.yml) and
[`examples/secure-pr-publish.yml`](examples/secure-pr-publish.yml):

1. The `pull_request` workflow analyzes with `contents: read`, keeps
   `comment-on-pr: "false"`, and uploads only `pr-report.json` under a fixed
   artifact name.
2. A `workflow_run` job downloads that exact artifact from the exact triggering
   run and invokes the publication-only companion action at a reviewed full
   commit SHA. It never checks out the PR revision.
3. `publish-pr-report` validates the schema, size, repository, PR number, event
   base/head SHAs, workflow run ID, workflow name, completed-comparison state, counts, and
   evidence before making an API request. It also confirms that the PR is still
   open at the reported head SHA. A mismatch stops publication.

Artifact report text is still untrusted. Markdown values are HTML-escaped,
table delimiters and line breaks are neutralized, HTML comment injection is
prevented, details are capped, and repository/API path components are encoded.
The publisher can only create or edit an issue comment on the validated PR. It
does not execute the artifact, invoke the analysis CLI, restore packages, or
load project files.

Never run the main analysis Action under `pull_request_target`: loading a .NET
project may execute repository-controlled MSBuild logic. The Action rejects
that event. A privileged `workflow_run` publisher is safe only when it consumes
the bounded structured report and trusted event metadata as shown; do not add a
checkout of the PR head or shell commands derived from artifact content.

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

An absolute quality gate compares the current report to a configured maximum
(for example, cyclomatic complexity 15). Regression detection compares the
same member across baseline and head using the CLI's compatible evidence and
ordering rules. Missing, unknown, ambiguous, or incompatible evidence is a
comparison limitation and never becomes a proven regression or a fabricated
metric.

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
`GITHUB_TOKEN`; keep `upload-sarif` disabled for an untrusted fork workflow.
The PR-report artifact handoff is intentionally limited to comments and does
not grant the publisher `security-events: write`.

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
Version `1.0.1` is the published package version exercised by the end-to-end
suite. Comparison currently assumes the configured entry-point path exists in
both revisions; an entry-point rename is unavailable rather than guessed.
Member/source-file renames, project additions/deletions, multiple target
frameworks, generated-code settings, and evidence compatibility are left to the
CLI snapshot matcher. The Action does not upload comparison SARIF, infer
alternate entry points, support non-Linux runners, or provide a process/network
sandbox. Comment discovery follows every GitHub API page before creating a new
report, and publication refuses a report whose head SHA is no longer the open
pull request head.

## Compatibility and versioning

Only Ubuntu GitHub-hosted runners are supported in `v1`. Linux tests cover
`.csproj`, `.sln`, `.slnx`, paths containing spaces, quality gates, JSON and
SARIF, snapshots, regression comparison, PR report generation, installation
errors, and cancellation. Windows and macOS have not passed equivalent
end-to-end suites and are explicitly unsupported.

Action releases follow Semantic Versioning independently of NuGet packages:

- PATCH: backward-compatible fixes and security updates.
- MINOR: backward-compatible functionality.
- MAJOR: a change to inputs/defaults, outputs, runner support, quality-gate or
  reporting semantics, or documented security requirements.

Use immutable `vX.Y.Z` release tags or a reviewed full commit SHA. The movable
`v1` compatibility reference is advanced only after a compatible immutable
release is verified; it is not itself a GitHub release. See
[`docs/maintainers.md`](docs/maintainers.md) and
[`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).

Release publication is never triggered by a push. The manually dispatched
**Release readiness** workflow, when dispatched from `main`, automatically
uses its exact commit SHA captured at dispatch (no manual SHA input). It
validates the selected version and commit, confirms tag uniqueness and the
published CLI, reruns required checks, and creates a deterministic manifest
and release notes without creating a tag or release.

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
- **PR comment was not published:** confirm the event is `pull_request`,
  comparison completed, `comment-on-pr` is `true`, and the job has
  `pull-requests: write`. Fork tokens are expected to be read-only; use the
  isolated `workflow_run` examples instead of weakening the analysis job.
- **A repeated run created a second comment:** the authenticated credential must
  be the same bot identity. The publisher deliberately refuses to edit a
  marked comment owned by another identity.
- **Artifact publication was rejected:** confirm the artifact came from the
  exact `workflow_run` ID/name and that its repository, PR number, and head SHA
  still match the trusted event. Do not bypass these checks.
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
bash tests/integration/test-pr-reporting-scripts.sh
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

## Public release verification

The [`v1.0.0` release](https://github.com/rodri-oliveira-dev/complexity-analysis-action/releases/tag/v1.0.0) is published
and points to the reviewed commit `2d807ef29ca03c685d224543a135d8c30dfe2c67`. The major `v1` alias remains to
be created and verified separately. Use the read-only
[Verify published Action release](.github/workflows/verify-published-release.yml)
workflow to check the exact release and, after it exists, its major tag target.
Test the Action from an
[external consumer repository](docs/external-consumer-validation.md).
Marketplace discoverability requires independent verification; neither the
release API nor this workflow proves it.
