# GAIA v0.9 B3 Start Here

GAIA v0.9 B3 adds deterministic recommendation ranking and prioritisation on top of the B1 project-health registry and B2 change-intelligence findings.

## What shipped

- deterministic recommendation generation from structured B1 and B2 evidence;
- explainable scoring with a versioned prioritisation policy;
- explicit blockers, dependencies, and lifecycle states;
- stable semantic fingerprints for idempotent recommendation refreshes;
- portfolio-style queue and per-project recommendation views;
- SQLite schema migration for recommendation persistence.

## What stayed out of scope

- B4 work-package generation;
- Windows Project Officer UI work;
- Dashboard execution or write controls;
- MicroGrow changes;
- automatic Codex invocation;
- automatic execution of recommendations.

## Read next

1. [Recommendation Architecture](RECOMMENDATION_ARCHITECTURE.md)
2. [Prioritisation Policy](PRIORITISATION_POLICY.md)
3. [Scoring Model](SCORING_MODEL.md)
4. [Recommendation Lifecycle](RECOMMENDATION_LIFECYCLE.md)
5. [Dependency and Blocker Model](DEPENDENCY_AND_BLOCKER_MODEL.md)
6. [Deduplication and Fingerprinting](DEDUPLICATION_AND_FINGERPRINTING.md)
7. [Security and Authority Boundary](SECURITY_AND_AUTHORITY_BOUNDARY.md)
8. [Validation Evidence](VALIDATION_EVIDENCE.md)
9. [Handoff to B4](HANDOFF_TO_B4.md)
