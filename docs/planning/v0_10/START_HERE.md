# GAIA v0.10 Start Here

GAIA v0.10 is the engineering programme intelligence planning milestone. It defines how GAIA reasons across projects, contracts, releases, and shared architecture while keeping human control intact.

## Frozen Baseline

- Release baseline: `gaia-v0.9.0`
- Planning branch: `planning/gaia-v0.10-programme-intelligence`
- Expected release version: `0.9.0`
- v0.9 is frozen and remains the compatibility baseline for this planning package.

## What v0.10 Is For

- represent approved project identity as a canonical project contract;
- register shared architecture entities with stable provenance;
- build deterministic dependency graphs across projects;
- analyze cross-project change impact without guessing;
- score programme-level priorities, roadmap states, and release trains;
- group project work packages into human-reviewed programme packages;
- expose programme read models through the existing GAIA surfaces.

## What v0.10 Is Not For

- autonomous Codex execution;
- arbitrary shell execution;
- external repository mutation;
- automatic merges or deployments;
- Dashboard approval authority;
- direct Dashboard database access;
- replacing deterministic backend logic with Flutter logic.

## Read This Package In Order

1. [Vision](GAIA_V0_10_VISION.md)
2. [Architecture](GAIA_V0_10_ARCHITECTURE.md)
3. [Security Boundary](GAIA_V0_10_SECURITY_BOUNDARY.md)
4. [Non-Goals](GAIA_V0_10_NON_GOALS.md)
5. [Project Contract Model](PROJECT_CONTRACT_MODEL.md)
6. [Architecture Registry Model](ARCHITECTURE_REGISTRY_MODEL.md)
7. [Dependency Graph Model](DEPENDENCY_GRAPH_MODEL.md)
8. [Change Impact Model](CHANGE_IMPACT_MODEL.md)
9. [Change Proposal Model](CHANGE_PROPOSAL_MODEL.md)
10. [Programme Roadmap Model](PROGRAMME_ROADMAP_MODEL.md)
11. [Release Train Model](RELEASE_TRAIN_MODEL.md)
12. [Programme Package Model](PROGRAMME_PACKAGE_MODEL.md)
13. [Decision and Provenance Model](DECISION_AND_PROVENANCE_MODEL.md)
14. [Windows Programme Workspace Plan](WINDOWS_PROGRAMME_WORKSPACE_PLAN.md)
15. [Dashboard Read-Only Programme Plan](DASHBOARD_READ_ONLY_PROGRAMME_PLAN.md)
16. [API, CLI and Client Plan](API_CLI_CLIENT_PLAN.md)
17. [Migration and Compatibility Plan](MIGRATION_AND_COMPATIBILITY_PLAN.md)
18. [Test Strategy](GAIA_V0_10_TEST_STRATEGY.md)
19. [Implementation Phases](GAIA_V0_10_IMPLEMENTATION_PHASES.md)
20. [Acceptance Criteria](GAIA_V0_10_ACCEPTANCE_CRITERIA.md)
21. [v0.9 to v0.10 Traceability](V0_9_TO_V0_10_TRACEABILITY.md)

## Recommended First Implementation Branch

After this planning PR merges, start with:

- `planning/gaia-v0.10-c1-project-contract-architecture-registry`

That branch should implement only the C1 scope:

- project contract storage and read models;
- architecture registry storage and read models;
- deterministic provenance and revision identity for those records.

## Maintenance Note

The post-release v0.9 validation noted dependency maintenance pressure, including a discontinued `flutter_markdown` package and several constrained Flutter/Dart versions. Treat that as a separate maintenance decision rather than mixing it into the v0.10 feature plan.
