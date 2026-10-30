# Release checklist

Reusable checklist for future versions. The initial
[`v1.0.0` release](https://github.com/rodri-oliveira-dev/complexity-analysis-action/releases/tag/v1.0.0) was published on
2026-10-30; the items below are **not** a retroactive assertion that every
Marketplace, external-consumer, or release-immutability check is complete.

- [ ] The requested version is a unique stable Semantic Version.
- [ ] CI, end-to-end, CodeQL, and release-readiness checks pass on the exact commit.
- [ ] Compatibility and public-contract changes have been assessed.
- [ ] `ComplexityAnalysis.Tool` is an exact published version and its .NET runtime is documented.
- [ ] No open critical security alert or unresolved release blocker remains.
- [ ] `main` requires review and passing checks; release immutability is enabled.
- [ ] Release notes and `release-manifest.json` match the exact release commit.
- [ ] External-consumer validation resolves the exact release commit SHA.
- [ ] Marketplace metadata passes and **Complexity Analysis** is accepted as unique.
- [ ] Marketplace categories are **Code quality** and **Continuous integration**.
- [ ] The repository owner has accepted the Marketplace Developer Agreement and enabled 2FA.
- [ ] A draft GitHub release is prepared with the immutable `vX.Y.Z` tag.
- [ ] Publication receives explicit maintainer approval.
- [ ] After publication, advance mutable `vX` (and optional `vX.Y`) only to a compatible release.
- [ ] Run read-only post-publication verification against the approved commit.
- [ ] Verify external consumption of `vX.Y.Z`, `vX`, and the full SHA; record consumer workflow URLs.
- [ ] Confirm Marketplace listing visibility independently in the owner's GitHub UI.
- [ ] Confirm the Marketplace page offers **Use latest version** for the published release.
- [ ] Once the listing is verified, update README installation examples and link to the real Marketplace page; deliberately update the pre-publication validator and its tests in the same change.
- [ ] Verify the Marketplace listing before adding its URL to public documentation.

Never force-update a release-specific tag. Do not create a GitHub release for
the mutable `v1` compatibility reference because immutable release tags cannot
move. See `docs/maintainers.md` for the complete process.
