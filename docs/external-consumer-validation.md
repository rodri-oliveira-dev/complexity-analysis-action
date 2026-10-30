# External consumer validation

Running the Action with `uses: ./` in its own repository tests implementation, not
the ability of other repositories to resolve a published tag. Complete this
independent check after an approved stable release.

## Preconditions

- The version-specific GitHub release (e.g. `v1.0.0`) is published.
- Its exact 40-character commit SHA is recorded in the release manifest.
- The maintained `v1` tag points to that commit.
- A separate test repository contains an actual C# project/solution.

## Consumer workflow

Create `.github/workflows/verify-complexity.yml` on a test branch of a
separate repository, replacing `REVIEWED_RELEASE_COMMIT_SHA` with the approved
full SHA and `Sample.slnx` with a real entry point:

```yaml
name: Verify Complexity Analysis Action
on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          persist-credentials: false
      - id: complexity
        uses: rodri-oliveira-dev/complexity-analysis-action@REVIEWED_RELEASE_COMMIT_SHA
        with:
          path: Sample.slnx
          max-cyclomatic-complexity: "100"
      - name: Assert reports
        shell: bash
        env:
          STATUS: ${{ steps.complexity.outputs.analysis-status }}
          REPORT: ${{ steps.complexity.outputs.report-path }}
        run: |
          test "$STATUS" = success
          test -s "$REPORT"
```

Run it using the exact reviewed SHA. Repeat by replacing the Action reference
with `@v1.0.0` and `@v1`. For each run, record the URL and result. The
template above is intentionally **not executable without substitution**; do
not treat any placeholder as a valid ref.

Validate opt-in features separately with:
[quality gates](../examples/quality-gates.yml),
[SARIF](../examples/sarif-upload.yml) and
[isolated PR publishing](../examples/secure-pr-publish.yml).
Use only the necessary permissions; do not give untrusted PR analysis
write-capable tokens.

| Check | Evidence to retain |
| --- | --- |
| Full SHA consumption | Workflow URL, resolved SHA, result |
| Immutable `v1.0.0` consumption | Workflow URL, resolved SHA, result |
| Maintained `v1` consumption | Workflow URL, resolved SHA, result |
| Marketplace listing | Owner-confirmed visible listing URL |
| Limitations | Supported runner and optional permissions |

The read-only [post-publication verifier](../.github/workflows/verify-published-release.yml)
checks GitHub release and tag objects. It does not prove Marketplace visibility,
Developer Agreement acceptance, or external consumer execution.
