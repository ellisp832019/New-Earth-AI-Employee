# GAIA v0.9 B1 Start Here

GAIA v0.9 B1 implements a local multi-project registry/cache and deterministic project-health snapshot model.

## What shipped

- local registry records for GAIA, MicroGrow V1, and the New Earth Command Dashboard;
- read-only project metadata with isolated inspection boundaries;
- deterministic project-health snapshots persisted in SQLite;
- portfolio-style aggregation over the latest health state for enabled projects;
- schema migration from the previous GAIA database version to the B1 schema version.

## What stayed out of scope

- B2 change intelligence;
- release recommendation automation;
- write permissions or output execution;
- Dashboard behaviour changes;
- MicroGrow repository changes.

## Read next

1. [Project Registry Implementation](PROJECT_REGISTRY_IMPLEMENTATION.md)
2. [Project Health Model](PROJECT_HEALTH_MODEL.md)
3. [Health Normalisation Rules](HEALTH_NORMALISATION_RULES.md)
4. [Database Migration](DATABASE_MIGRATION.md)
5. [Security and Isolation Proof](SECURITY_AND_ISOLATION_PROOF.md)
6. [Validation Evidence](VALIDATION_EVIDENCE.md)
7. [Handoff to B2](HANDOFF_TO_B2.md)
