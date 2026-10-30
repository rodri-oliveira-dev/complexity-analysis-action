# Release-readiness evidence

Audit date: 2026-10-30. Target Action release: `v1.0.0`.

## Baseline and repository state

- The validated default branch was `main` at
  `f16c717bff9235e1dfc03dffcf26c64f3da2d275`.
- Phase 1 was merged by PR #1 and Phase 2 by PR #2. Both CI and End-to-end
  workflows passed on the default-branch merge commits.
- At audit time the Action repository had no tags, releases, open pull requests,
  rulesets, or branch protection.
- Default workflow permissions were read-only, Actions could not approve pull
  requests, private vulnerability reporting was enabled, and Dependabot reported
  no open alerts. Immutable releases were disabled.

These settings are external release blockers: protect `main` with the required
CI, End-to-end, and CodeQL checks and enable immutable releases before publishing.
The release-readiness workflow inspects effective branch rules, requires an
explicit maintainer confirmation for the admin-only immutability setting, and
refuses eligibility when either is absent.

## Dependency evidence

NuGet.org published `ComplexityAnalysis.Tool` 1.0.0 and 1.0.1 at audit time.
The Action pins 1.0.1; its signed package targets `net10.0`, requires
`Microsoft.NETCore.App` 10.0, and records analysis-engine commit
`24779a2f8b93a9c5195cf323349bb32fa30803c0`. The Action installs .NET SDK
10.0.403 and rejects floating or malformed package versions. Action SemVer is
independent of this package version.

Every external Action reference was compared with its documented release tag.
The audit corrected the CodeQL pin to the actual `v4.31.9` commit. Static checks
reject non-SHA external references.

## Architecture and threat review

The composite Action remains an orchestrator: validation, installation,
analysis, comparison, report validation/rendering, and final policy application
stay in separate scripts. Metric and regression semantics remain owned by the
published CLI. This avoids a second analysis implementation and preserves the
existing input/output and exit-code contracts.

Confirmed corrections made for release readiness:

- checkout credentials are not persisted in analysis workflows or examples;
- analysis and CLI temporary directories are bounded and cleaned;
- a privileged publisher verifies the PR is still open at the reported head,
  preventing a late run from overwriting a newer report;
- the isolated publisher example serializes per-PR updates;
- CodeQL, Dependabot, deterministic release artifacts, and repository-setting
  eligibility checks are automated.

The remaining duplicated safe-environment construction in analysis and snapshot
execution was intentionally retained: consolidating it would add coupling to
stable security-sensitive paths without changing behavior. MSBuild project
loading is not a sandbox. Untrusted analysis must remain read-only and secretless,
and privileged publication must never execute the analyzed revision.

## Compatibility matrix

| Capability | Ubuntu | Windows | macOS |
| --- | --- | --- | --- |
| `.csproj`, `.sln`, `.slnx` and spaces in paths | End-to-end covered | Unsupported | Unsupported |
| JSON, SARIF, and quality gates | End-to-end covered | Unsupported | Unsupported |
| Snapshots and regression comparison | End-to-end covered | Unsupported | Unsupported |
| PR report generation/publication guards | Unit/integration covered | Unsupported | Unsupported |
| Installation errors and cancellation | Integration covered | Unsupported | Unsupported |
| Optional SARIF upload policy | Validation/failure policy covered; server acceptance depends on repository Code Scanning | Unsupported | Unsupported |

No cross-platform support is claimed. GitHub-hosted Ubuntu is the only supported
runner contract for `v1.0.0`.

## Publication boundary

No workflow in this repository publishes on push. Manual release readiness only
generates notes, a hash manifest, and repository-settings evidence for an exact
version and commit. It does not create or move tags, create a GitHub release,
merge a branch, or submit to Marketplace.
