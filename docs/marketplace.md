# GitHub Marketplace publication and verification

## Current release status (2026-10-30)

- **GitHub Release:** [Complexity Analysis Action v1.0.0](https://github.com/rodri-oliveira-dev/complexity-analysis-action/releases/tag/v1.0.0) is published.
- **Release tag:** `v1.0.0` resolves to `2d807ef29ca03c685d224543a135d8c30dfe2c67`.
- **Moving major alias:** `v1` has not been created yet; do not use `@v1` in consumer examples.
- **Marketplace listing:** its public URL and **Use latest version** interface have not been independently verified. Do not advertise a Marketplace URL until verified.
- **Release immutability:** the GitHub Releases API reported `immutable: false` for `v1.0.0` at verification time. The repository's tag ruleset protects version-specific tags, but tag protection is not the same as immutable GitHub Releases.

A root `action.yml` makes this repository directly reusable as a GitHub Action.
A published GitHub Release alone does not establish a public Marketplace listing.

## Marketplace metadata

- Product name: **Complexity Analysis**
- Description: **Analyze C# complexity with quality gates, JSON/SARIF reports, and proven regression detection.**
- Primary category: **Code quality** (`code-quality`)
- Secondary category: **Continuous integration** (`continuous-integration`)
- Branding: Feather `activity` icon with `purple` background
- First stable version: `v1.0.0`

## Positioning

Complexity Analysis helps .NET teams analyze C# complexity in CI, enforce
explicit quality gates, compare pull-request changes, generate JSON and SARIF,
and review proven regressions in GitHub. Results are based on structural metrics
and estimated algorithmic complexity; they are not runtime benchmarks,
automatic optimizations, or exact predictions of execution time.

## Owner verification of Marketplace publication

1. Open the published [v1.0.0 release](https://github.com/rodri-oliveira-dev/complexity-analysis-action/releases/tag/v1.0.0) while signed in as the owner and inspect the Marketplace publication state.
2. If the GitHub Marketplace listing is not yet public, follow GitHub's [Publish an Action in the Marketplace](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace) procedure and verify the **Publish this Action to the GitHub Marketplace** selection.
3. Open the resulting **public Marketplace listing** independently and confirm that **Use latest version** is available. Only then record the actual listing URL in the README.
4. Review repository release immutability settings and do not equate a protected `v1.0.0` tag with `immutable: true`.
5. Create the separate compatible `v1` reference after owner approval, pointing to the same reviewed commit. Do not create a GitHub Release for `v1`.

The repository cannot infer Marketplace listing visibility or the owner's
Developer Agreement acceptance from the GitHub Releases API.

## Post-publication verification

After `v1` exists, run [Verify published Action release](../.github/workflows/verify-published-release.yml)
with version `v1.0.0`, commit `2d807ef29ca03c685d224543a135d8c30dfe2c67`, and major verification enabled.
Until `v1` exists, run the verifier with major verification disabled, so it
checks only the published release and its version-specific tag.

Follow [external consumer validation](external-consumer-validation.md) in a
separate repository for full-SHA and `v1.0.0` consumption. Include the `v1`
reference only after its tag is created and independently verified.

The verifier does not publish tags, releases, or Marketplace listings.
