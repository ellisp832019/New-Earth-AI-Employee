# Architecture Evidence

## Authority Model

- Platform Core: declared/canonical architecture authority.
- NEOS: observed/reconciled engineering authority.
- GAIA: interpretation, prioritisation, and work preparation.

## Live Changes

- Added `src/gaia/governance_context.py` for NEOS governance ingestion and GAIA interpretation.
- Added read-only governance API and CLI surfaces.
- Added governance-aware daily brief integration.
- Added local cache/history storage for governance snapshots.

## B1 Convergence

- B1 wording now describes a local project registry/cache and health context.
- B1 live project-health wording now uses local-registry/local-context language.

## Boundary

The implementation does not create a second canonical engineering registry.
