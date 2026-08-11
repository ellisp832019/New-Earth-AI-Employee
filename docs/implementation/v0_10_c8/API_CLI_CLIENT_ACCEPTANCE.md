# API, CLI, and Client Acceptance

## OpenAPI and API

- `scripts/export_openapi_contract.ps1` exported the contract successfully after the version bump.
- `contracts/openapi/gaia-v1.json` is current and now reports backend version `0.10.0`.
- no unintended mutation endpoints were introduced.
- the C6 internal Windows workspace route remains excluded from the public contract where intended.

## CLI

The release preserves the supported v0.10 read commands for:

- programme overview and programme summary;
- architecture lists and relationships;
- dependency graph and dependency findings;
- change impact and recommendations;
- release trains;
- programme packages.

## Integration Client

- `dart test` in `packages/gaia_integration_client` passed;
- the public programme read methods parse correctly;
- healthy, unavailable, incompatible, stale, unknown, and partial/missing states remain represented;
- v0.8/v0.9 compatible behavior remains intact.
