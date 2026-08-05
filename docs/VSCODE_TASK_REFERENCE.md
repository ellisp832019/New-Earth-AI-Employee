# VS Code Task Reference

## Validation Tasks

- `GAIA: Validate Managed Backend Lifecycle` runs the focused safe-start, check, stop, restart, and status lifecycle validation.
- `GAIA: v0.5.1 Release Readiness` runs the repaired managed-backend and workspace readiness checks.
- `v0.5 validation` runs the Python checks, Flutter checks, package checks, OpenAPI export, manifest validation, and integration contract validation.
- `validate vscode workspace` checks the expected CLI groups and workspace wiring.

## Operator Notes

- Use the task runner when you want a single button check before publishing.
- Use the CLI directly when you need to inspect a specific manifest, action, or receipt.
- Use the managed-backend tasks rather than stopping `python` processes manually.
