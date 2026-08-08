# GAIA v0.10 Implementation Phases

## Phase Model

The preferred sequence is:

- C1 - Project Contract + Architecture Registry
- C2 - Cross-Project Dependency Graph
- C3 - Change Impact Intelligence
- C4 - Programme Roadmap + Release Train Intelligence
- C5 - Human-Reviewable Programme Packages
- C6 - Windows Programme Intelligence Workspace
- C7 - API / CLI / Integration Client + Read-Only Dashboard Summary
- C8 - Cross-Repository Acceptance + v0.10 Release Closeout

## Optional Maintenance Track

If dependency maintenance becomes a blocker, handle it as a separate small maintenance PR and not as part of the v0.10 feature chain.

## Per-Phase Pattern

Each phase should have:

- one branch;
- one focused PR;
- explicit acceptance criteria;
- validation evidence;
- a handoff document that defines the next phase.

## Recommended Branch Naming

Use a consistent pattern such as:

- `planning/gaia-v0.10-c1-project-contract-architecture-registry`
- `planning/gaia-v0.10-c2-dependency-graph`
- `planning/gaia-v0.10-c3-change-impact`

That keeps implementation work traceable to the plan.
