# GAIA v0.5.0 Release Notes

GAIA v0.5.0 introduces the permissioned output workspace.

## Highlights

- Permission manifests for output actions.
- GAIA-owned output workspace enforcement.
- Exact previews and content hashes for writes.
- Explicit approval and user-triggered execution.
- Execution receipts, backups, and rollback support.
- Reusable Dart integration client and GAIA v1 compatibility contract.
- Windows control-centre screens for permissions, actions, and receipts.

## Safety Improvements

- Writes are default-deny.
- The target path must be canonical and inside the allowlisted workspace.
- A changed manifest or target invalidates dependent execution.

## Validation

- Python tests, type checks, and linting pass.
- Flutter analysis and tests pass.
- Windows debug and release builds pass.
- OpenAPI and integration contract validation pass.
- Live acceptance workflow verified create, update, receipt, rollback, and read-only MicroGrow behavior.
