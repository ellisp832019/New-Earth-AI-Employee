# GAIA v0.10 C1 Start Here

GAIA v0.10 C1 introduces the canonical project contract and the architecture registry foundation.

## Baseline

- Release baseline: `gaia-v0.9.0`
- Branch: `planning/gaia-v0.10-c1-project-contract-architecture-registry`
- Expected release version: `0.9.0`

## What C1 Is For

- create a deterministic project contract read model for each configured project;
- register architecture entities with stable identity keys and provenance;
- register architecture relationships between known entities;
- preserve the v0.9 release line and existing project compatibility;
- provide a migration-safe schema extension for the local SQLite database.

## What C1 Is Not For

- dependency-graph traversal;
- change-impact analysis;
- programme roadmap scoring;
- release-train planning;
- API or CLI expansion beyond the new registry read models;
- changes to Dashboard or MicroGrow.

## Read This Package In Order

1. [Project Contract Model](PROJECT_CONTRACT_MODEL.md)
2. [Architecture Registry Model](ARCHITECTURE_REGISTRY_MODEL.md)
3. [Validation Evidence](VALIDATION_EVIDENCE.md)
4. [Handoff to C2](HANDOFF_TO_C2.md)
