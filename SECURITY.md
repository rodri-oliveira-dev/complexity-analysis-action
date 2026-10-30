# Security Policy

## Supported versions

Security fixes are provided for the latest `v1` release. Consumers with a
strict supply-chain policy should pin the Action to a reviewed full commit SHA.

## Reporting a vulnerability

Use GitHub private vulnerability reporting for this repository. Do not open a
public issue for suspected token exposure, command injection, artifact
substitution, or unsafe project evaluation. Include the affected Action commit,
workflow event, runner image, and a minimal reproduction when possible.

## Trust boundary

The analyzer loads MSBuild projects and therefore may execute project-controlled
MSBuild logic. Analyze untrusted pull requests only with a read-only token, no
secrets, and no privileged credentials. Never run this Action with
`pull_request_target`. The documented `workflow_run` publisher validates and
renders a bounded JSON report; it must never check out or execute pull-request
code.
