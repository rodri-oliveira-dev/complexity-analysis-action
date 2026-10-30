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
   readiness** using **Run workflow** from `main`, with `version` (for example
   `v1.0.0`) and the immutability confirmation. No commit input is needed:
   the workflow uses the exact `github.sha` of `main` captured at dispatch
   time and rejects runs started from other branches. The workflow validates
   rather than publishes.
3. Review the generated notes, manifest, Marketplace metadata report, repository
   settings, and exact-commit CI/End-to-end/CodeQL results. Use the SHA saved in
   the release manifest for the approved tag even if `main` has advanced.
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

## Post-publication verification

1. After an owner-approved stable release, create or advance the compatible
   major-version Git tag according to the immutable-release policy above.
2. Dispatch [Verify published Action release](../.github/workflows/verify-published-release.yml)
   with the exact published tag and release commit SHA. Keep major verification
   enabled after the `v1` tag is available.
3. Review `publication-verification.json`; it checks published-release metadata
   and Git objects, including annotated tags, but cannot verify Marketplace.
4. Validate release SHA and tags from an independent repository following
   [external consumer validation](external-consumer-validation.md), recording
   workflow URLs and outcomes.
5. Confirm Marketplace listing visibility in the UI and record its URL.

These verification steps are read-only and never create or move tags, create
releases, or publish a Marketplace listing.
