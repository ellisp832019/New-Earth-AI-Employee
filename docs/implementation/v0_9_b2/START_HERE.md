# GAIA v0.9 B2 Start Here

GAIA v0.9 B2 adds deterministic snapshot comparison and change intelligence on top of the B1 project-health registry.

## What shipped

- deterministic comparison of two project-health snapshots;
- structured change findings with severity, confidence, and direction;
- noise filtering for timestamp-only and ID-only differences;
- historical comparison and finding queries;
- portfolio-style change summaries for enabled projects;
- SQLite schema migration for comparison and finding persistence.

## What stayed out of scope

- B3 recommendation and prioritisation;
- B4 work-package generation;
- Windows Project Officer UI work;
- Dashboard changes;
- MicroGrow changes;
- automatic execution.

## Read next

1. [Change Intelligence Architecture](CHANGE_INTELLIGENCE_ARCHITECTURE.md)
2. [Change Finding Model](CHANGE_FINDING_MODEL.md)
3. [Detector Rules](DETECTOR_RULES.md)
4. [Noise Filtering and Fingerprinting](NOISE_FILTERING_AND_FINGERPRINTING.md)
5. [Database Migration](DATABASE_MIGRATION.md)
6. [Security and Isolation Proof](SECURITY_AND_ISOLATION_PROOF.md)
7. [Validation Evidence](VALIDATION_EVIDENCE.md)
8. [Handoff to B3](HANDOFF_TO_B3.md)
