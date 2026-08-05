# Changelog

## [gaia-v0.5.0] - 2026-08-05

### Added

- Permission manifests that define allowed action types, target roots, risk ceilings, overwrite policy, backup requirement, and rollback requirement.
- GAIA-owned output workspace enforcement with explicit path safety checks and default-deny behavior.
- Exact write previews, deterministic content hashing, execution receipts, backup records, and rollback records.
- Explicit user-triggered execution flow for output actions.
- Reusable `gaia_integration_client` Dart package for dashboard and operator integrations.
- GAIA v1 OpenAPI compatibility contract and integration summary endpoints.
- Windows control-centre screens for permissions, actions, and receipts.
- Live acceptance workflow proving create, update, receipt, and rollback behavior.

### Changed

- Backend schema version advanced to support permission manifests, output actions, action previews, receipts, backups, and rollbacks.
- Desktop and CLI surfaces now expose the permissioned output workflow.

## [gaia-v0.4.0] - 2026-08-05

- Controlled tasks, drafts, approvals, and daily brief foundation.
