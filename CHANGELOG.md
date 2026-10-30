# Changelog

This project follows Semantic Versioning independently of
`ComplexityAnalysis.Tool` and the analysis engine.

## [1.0.0] - Unreleased

### Added

- Composite Action support for `.csproj`, `.sln`, and `.slnx` analysis on Ubuntu.
- Deterministic JSON, SARIF, quality-gate, snapshot, and regression reporting.
- Secure direct and isolated pull-request reporting modes.
- Reproducible CLI installation and release-readiness automation.

### Security

- Minimum workflow permissions, full-SHA Action pins, bounded report validation,
  isolated temporary state, and explicit rejection of `pull_request_target`.
