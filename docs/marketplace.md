# GitHub Marketplace publication plan

## What appears on the repository page

A public repository with the root `action.yml` is a reusable GitHub Action, but **merging a documentation PR does not publish a Marketplace listing or create an install button**. Before release, the README highlights that this is a GitHub Action and provides a complete workflow using a reviewed commit SHA. The `action.yml` file also exposes the owner-only **Draft a release** banner.

After the owner publishes `v1.0.0` with **Publish this Action to the GitHub Marketplace** selected, consumers can visit its dedicated Marketplace listing and select **Use latest version** to copy the `uses:` snippet. Once the listing and both version references are verified, update the public README with the *verified* Marketplace URL and an `@v1` quick-start example. At that point the pre-publication link guard in `scripts/validate-distribution.py` and its tests must also be updated intentionally, so CI does not incorrectly reject a legitimate listing link. Do not invent a Marketplace URL or advertise a version ref before it is available.

GitHub's [official publication procedure](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace) is the authoritative reference.


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
