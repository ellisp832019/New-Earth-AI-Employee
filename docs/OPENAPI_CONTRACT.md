# OpenAPI Contract

GAIA v0.5 publishes a generated OpenAPI document at `contracts/openapi/gaia-v1.json`.

## Purpose

- Document the external API surface for dashboards and integration clients.
- Provide a compatibility anchor for `gaia-v1`.
- Support validation of the new permissioned output workspace endpoints.

## Validation

The repository includes `scripts/export_openapi_contract.ps1` and `scripts/validate_integration_contract.ps1` to keep the contract export and compatibility checks reproducible.

## Scope

The contract includes the standard project, task, draft, approval, brief, and model endpoints, plus the v0.5 permissions, actions, receipts, and integration summary routes.
