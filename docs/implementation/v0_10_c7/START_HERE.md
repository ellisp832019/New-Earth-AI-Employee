# GAIA v0.10 C7A Start Here

## Scope

C7A establishes the public, read-only programme surfaces for GAIA:

- public programme API routes;
- public CLI read commands;
- integration-client programme models and methods;
- reusable dashboard-module programme summary surface.

## What Was Added

- `/integration/v1/programme/summary` and related public read routes;
- `gaia programme`, `gaia architecture`, `gaia impact`, `gaia release-train`, and `gaia programme-package` CLI groups;
- `GaiaIntegrationClient` programme and dependency methods;
- `GaiaProgrammeSummaryView` for the dashboard module;
- refreshed OpenAPI contract export.

## Safety Boundary

- read-only surfaces only;
- no VERSION changes;
- no MicroGrow changes;
- no direct repository mutation from the new programme read surfaces;
- no release publication.

## Validation

Use the validation evidence in `docs/implementation/v0_10_c7/VALIDATION_EVIDENCE.md`.
