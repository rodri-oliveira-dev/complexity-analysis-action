# Branch and release tag rulesets

This repository maintains **two importable GitHub rulesets**, reviewed with
the Action code. The JSON files in `.github/rulesets/` are the proposed
source of truth, **not automatic GitHub settings**. GitHub does not activate
rulesets because files have been committed.

| File | Applies to | Enforcement |
| --- | --- | --- |
| [main.json](../.github/rulesets/main.json) | Default branch (`main`) | PRs, CI checks, no deletion/force-push, linear history |
| [release-tags.json](../.github/rulesets/release-tags.json) | Release-specific tags `vX.Y.Z` | Disallow updates and deletion after creation |

## Branch policy

- Every change to `main` is merged through a PR; use **squash** or **rebase**
  to preserve linear history.
- Required passing checks are the **exact observed GitHub Actions job names**:
  `static-validation`, `script-integration`,
  `Published CLI / pull-request regression`, `Published CLI / csproj`,
  `Published CLI / sln`, `Published CLI / slnx`, `quality-gates`,
  `expected-errors`, and CodeQL `analyze`.
- The checks are constrained to **GitHub Actions** (integration ID `15368`)
  to prevent unrelated apps from supplying matching names.
- Branches must be up to date with `main` before merging; resolve review
  threads first.
- Required approvals: **zero**, deliberately. This is a single-maintainer
  repository; requiring another person's approval would make self-authored
  PRs impossible to merge. Review remains recommended and may be required if
  an additional maintainer is designated.
- No configured bypass actors. Do not weaken required checks or add an
  unconditional administrator bypass to work around a failing CI check.

The stricter checks may initially block open Dependabot PRs if their CodeQL
job fails. Fix those errors rather than bypassing the ruleset.

## Release tag policy

`v*.*.*` matches version-specific tags such as `v1.0.0` and `v1.2.3`.
Once created, these tags **cannot be modified or deleted** under the active
ruleset. There is deliberately **no creation restriction**, because the
owner-controlled GitHub Marketplace release workflow creates version tags.

The **movable** major alias `v1` (and optional minor alias `v1.2`) is
outside this rule, so a reviewed compatible release can advance it.

Do not add a blanket `~ALL` tag update rule: that would block the planned
major-version alias. This is a ref-pattern protection rule, not a strict
Semantic Versioning parser. Release input validation remains in
`scripts/prepare-release.py`.

## Apply through GitHub

1. Review and merge the ruleset configuration PR, or download the two JSON
   files from the PR branch if importing before merge.
2. Open **Settings → Rules → Rulesets** in this repository.
3. Select **New ruleset → Import a ruleset**, choose `main.json`, review
   the targets, required check names, and active enforcement, then **Create**.
4. Repeat for `release-tags.json`. Verify that `v1` is not included.
5. Inspect the new active rulesets and the **Rules insights** panel. Check that
   no special bypass is enabled and that protection applies to `main`.
6. Test with an ordinary PR; do not test immutable tag protection by creating
   or deleting a production release tag.

Direct link to settings:
https://github.com/rodri-oliveira-dev/complexity-analysis-action/settings/rules

### Alternative: GitHub CLI (requires repository Administration: write)

Run these commands **from the repository root**, authenticated with an owner
account that can manage repository rulesets:

```bash
gh auth status
gh api repos/rodri-oliveira-dev/complexity-analysis-action/rulesets \
  --jq '.[] | {id, name, enforcement}'
# Only when the names do NOT already exist:
gh api --method POST repos/rodri-oliveira-dev/complexity-analysis-action/rulesets \
  --input .github/rulesets/main.json
gh api --method POST repos/rodri-oliveira-dev/complexity-analysis-action/rulesets \
  --input .github/rulesets/release-tags.json
gh api repos/rodri-oliveira-dev/complexity-analysis-action/rulesets \
  --jq '.[] | {id, name, enforcement}'
```

Avoid rerunning POST without listing existing rulesets, or duplicate policies
will be created. Ruleset creation is an administration API operation, separate
from Git commit/push permissions.

## Release readiness interplay

The `Release readiness` workflow checks that `main` is protected and the
maintainer confirms immutable GitHub releases. This tag ruleset is **additional
defense**, not a substitute for enabling immutable releases in GitHub Settings.
When publishing `v1.0.0`, create that immutable release-specific ref normally
and only then advance the separate `v1` compatibility ref, as described in
[maintainer guidance](maintainers.md).

The JSON rulesets do not run automatically and no tags/releases are created by
the configuration PR.
