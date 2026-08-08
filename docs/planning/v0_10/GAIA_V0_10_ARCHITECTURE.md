# GAIA v0.10 Architecture

## Preserved Stack

- GAIA Python/FastAPI remains the canonical intelligence and state layer.
- GAIA Windows Control Centre remains the trusted operator workspace.
- The GAIA integration client remains the supported external client boundary.
- The New Earth Dashboard remains read only.

## Design Rule

Programme logic stays in Python. Flutter renders backend-owned read models and does not recompute the canonical graph, impact, or scoring logic.

## New Service Boundaries

- `ProjectContractService` for contract revision and lookup;
- `ArchitectureRegistryService` for shared entity identity and provenance;
- `DependencyGraphService` for deterministic traversal and cycle detection;
- `ChangeImpactService` for impact analysis and evidence freshness;
- `ProgrammeRoadmapService` for deterministic programme prioritisation;
- `ReleaseTrainService` for coordinated release sequencing;
- `ProgrammePackageService` for grouped reviewable programme work.

## Canonical Data Flow

1. Approved project and architecture records are stored in GAIA.
2. Deterministic services derive graphs, impact, roadmap, and release-train views.
3. The Windows app and Dashboard consume read-only models.
4. Human review is required before any handoff or approval state changes.

## Provenance Rule

Every programme-level claim must point back to a revisioned record, repository SHA, validation result, or derived graph snapshot. Unknown or stale evidence stays visible as unknown or stale.
