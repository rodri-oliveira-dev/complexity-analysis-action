# Maintainer guide

## Version ownership

The Action uses independent Semantic Versioning. PATCH releases contain
backward-compatible fixes or security updates; MINOR releases add compatible
functionality; MAJOR releases change a documented public contract. CLI, analyzer,
and MCP versions never determine the Action version. Inputs and defaults,
outputs, supported runners, gate behavior, reporting semantics, and security
requirements are public contracts.

The current compatibility baseline is Ubuntu GitHub-hosted runners, .NET SDK
10.0.403, and the exact `ComplexityAnalysis.Tool` version in `action.yml`. The
package targets `net10.0` and requires `Microsoft.NETCore.App` 10.0. Windows and
macOS are not supported until dedicated end-to-end jobs pass.

## Release preparation

1. Merge reviewed changes to protected `main` after CI, end-to-end, and CodeQL pass.
2. Verify immutable releases in repository settings, then dispatch **Release
   readiness** with that confirmation, `version` (for example `v1.0.0`), and the
   full 40-character commit SHA. The workflow validates rather than publishes.
3. Review the generated notes, manifest, Marketplace metadata report, repository
   settings, and exact-commit CI/End-to-end/CodeQL results.
4. Confirm the repository has no critical alert and immutable releases remain enabled.
5. Create a draft release for `vX.Y.Z`, attach any reviewed artifacts, and obtain
   explicit approval before publication. For the initial release, use the
   `action.yml` Marketplace banner and the owner procedure in `marketplace.md` so
   the release and listing are published together. Publication locks that tag.

The release-specific tag is immutable and is never moved or reused. Consumers
may pin it or, for the strongest reproducibility, the manifest's commit SHA.

## Compatibility references

`v1` is a mutable Git reference, not a GitHub release. After a compatible
`v1.x.y` release is published and verified, compare the target, create or update
the local annotated `v1` tag, and push the single tag with an explicit lease:

```bash
git fetch origin --tags
git tag -f -a v1 v1.x.y -m "Advance v1 to v1.x.y"
git push --force-with-lease=refs/tags/v1:<previous-object-id> origin refs/tags/v1
```

Record the old and new object IDs in the release approval. Never use a blanket
`git push --force --tags`, and never move `v1.0.0`. An optional `v1.x` reference
may follow the same policy for patch-only updates.

## Repository settings

Require pull requests and the CI, End-to-end, and CodeQL checks on `main`.
Keep default workflow permissions read-only, prevent Actions from approving pull
requests, enable Dependabot/security alerts and private vulnerability reporting,
and require full-SHA Action pins where repository policy supports it.
