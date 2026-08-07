# Dashboard Summary Architecture

The GAIA dashboard module remains a thin, read-only embedding surface over `GaiaIntegrationClient`.

## Components

- `GaiaDashboardController` coordinates legacy v0.8 data and B7 Project Officer summaries.
- `GaiaDashboardView` renders tabbed, read-only summaries.
- `GaiaIntegrationClient` remains the canonical transport layer.

## Design choices

- keep the existing v0.8 surfaces usable
- add a dedicated Project Officer tab
- preserve explicit unavailable, stale, partial, and incompatible states
- avoid duplicating Project Officer business logic in Dart

## Summary model

The dashboard surfaces backend-provided data for:

- portfolio health
- recommendations
- blocked projects
- approvals waiting for review
- stale evidence
- recent completed work
- trust alerts

The module only formats and groups server-returned records for presentation.
