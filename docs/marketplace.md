# GitHub Marketplace publication plan

## Proposed listing

- Product name: **Complexity Analysis**
- Description: **Analyze C# complexity with quality gates, JSON/SARIF reports,
  and proven regression detection.**
- Primary category: **Code quality** (`code-quality`)
- Secondary category: **Continuous integration** (`continuous-integration`)
- Branding: Feather `activity` icon with `purple` background
- Initial Action version: `v1.0.0`

The name was not found in Marketplace search during the 2026-10-30 preflight.
GitHub validates uniqueness authoritatively only in the **Release Action** form;
if it rejects the preferred name, use **C# Complexity Analysis** and rerun all
metadata checks before publication.

## Positioning

Complexity Analysis helps .NET teams analyze C# complexity in CI, enforce
explicit quality gates, compare pull-request changes, generate JSON and SARIF,
and review proven regressions in GitHub. Results are based on structural metrics
and estimated algorithmic complexity. They are not runtime benchmarks, automatic
performance optimizations, or precise predictions of execution time.

## Owner-only publication checklist

- [ ] Sign in as the repository owner and confirm two-factor authentication.
- [ ] Open the repository `action.yml` and select **Draft a release** from the
      Marketplace banner.
- [ ] Accept the GitHub Marketplace Developer Agreement if GitHub prompts for it.
- [ ] Confirm the metadata panel says **Everything looks good!** and the unique
      name is accepted.
- [ ] Select **Code quality** as primary and **Continuous integration** as secondary.
- [ ] Select **Publish this Action to the GitHub Marketplace**.
- [ ] Use the reviewed `v1.0.0` release commit, title
      `Complexity Analysis Action v1.0.0`, and the generated release notes.
- [ ] Publish only after required checks and explicit release approval.
- [ ] Verify the release and Marketplace listing, then create the separate `v1`
      reference at the same validated commit. Never create a GitHub release for `v1`.
- [ ] Verify external consumption through `v1.0.0`, `v1`, and the full commit SHA.

Do not add a Marketplace link to the README until the listing is visible. GitHub
Marketplace publication and Developer Agreement acceptance cannot be represented
as complete by repository automation.

## Verification after owner approval

After publishing the stable release and maintaining the separate `v1` reference,
run [Verify published Action release](../.github/workflows/verify-published-release.yml)
with the exact published version and full approved commit SHA. This read-only
workflow resolves annotated and lightweight Git tags and rejects mismatches.

Follow [external consumer validation](external-consumer-validation.md) from a
separate repository, testing full-SHA, `v1.0.0`, and `v1` references. Check
the Marketplace listing in the GitHub UI independently: the GitHub Release API
does not prove Marketplace listing visibility or agreement acceptance.
