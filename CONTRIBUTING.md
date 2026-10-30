# Contributing

Use a topic branch and keep changes focused on this Action. Preserve documented
inputs, outputs, exit semantics, and Linux support unless the change includes an
explicit compatibility assessment.

Before opening a pull request, run on Ubuntu:

```bash
bash scripts/static-checks.sh
bash tests/integration/test-action-scripts.sh
bash tests/integration/test-comparison-scripts.sh
bash tests/integration/test-pr-reporting-scripts.sh
bash tests/integration/test-published-cli.sh
bash tests/integration/test-pr-regression-e2e.sh
```

All external Actions must use reviewed full commit SHAs. Do not add a floating
NuGet version, a write token to untrusted analysis, or a workflow that publishes
from an ordinary push. Report security defects through `SECURITY.md`.
