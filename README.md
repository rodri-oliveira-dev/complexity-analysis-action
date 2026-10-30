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
| `output-directory` | No | `complexity-analysis-reports` | Workspace directory for the JSON report. |
| `include-generated` | No | `false` | Passes `--include-generated` when `true`. |
| `detect-duplicates` | No | `false` | Passes `--detect-duplicates` when `true`. |

Boolean inputs accept only the lowercase strings `true` and `false`.

## Outputs

| Output | Description |
| --- | --- |
| `report-path` | Absolute path to `complexity-analysis-report.json`. |
| `analysis-status` | `success` after a successful analysis, or `failed` when CLI execution fails. |
| `tool-version` | Exact CLI package version used. |

## Behavior and safety

- The Action sets up .NET 10 and installs the exact requested CLI version from
  an explicit NuGet.org-only configuration into an isolated temporary tool
  directory.
- Input and output paths must resolve inside `GITHUB_WORKSPACE`.
- Inputs are passed through environment variables and arguments are built as a
  Bash array. Input text is never evaluated as a shell command.
- Missing paths, unsupported extensions and runners, malformed versions,
  installation errors, and CLI failures produce explicit workflow errors.
- The report format is JSON. Quality-gate and richer reporting inputs can be
  added later without coupling the Action version to the CLI version.

The CLI supports `.csproj`, `.sln`, and `.slnx` inputs and requires .NET 10.
Version `1.0.0` is the first public package version used by this Action.

## Development validation

From a Bash environment on Ubuntu:

```bash
bash -n scripts/*.sh
shellcheck scripts/*.sh
actionlint
```

The repository CI exercises the local Action against sample `.csproj`, `.sln`,
and `.slnx` entry points, including paths containing spaces.
