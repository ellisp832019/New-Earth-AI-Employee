# GAIA v0.10 C2 Start Here

GAIA v0.10 C2 derives the canonical cross-project dependency graph from the C1 project contract and architecture registry records.

## Baseline

- Release baseline: `gaia-v0.9.0`
- Branch: `planning/gaia-v0.10-c2-dependency-graph`
- Expected release version: `0.9.0`

## What C2 Is For

- build a deterministic dependency graph from approved/current C1 records;
- answer direct and transitive dependency queries;
- answer reverse dependency queries;
- detect cycles, shared dependencies, orphans, and unresolved declarations;
- provide a canonical graph fingerprint without new storage.

## What C2 Is Not For

- change-impact scoring;
- roadmap prioritisation;
- release-train sequencing;
- programme package generation;
- public API/CLI/Dashboard exposure;
- any new database schema.

## Read This Package In Order

1. [Dependency Graph Model](DEPENDENCY_GRAPH_MODEL.md)
2. [Validation Evidence](VALIDATION_EVIDENCE.md)
3. [Handoff to C3](HANDOFF_TO_C3.md)
