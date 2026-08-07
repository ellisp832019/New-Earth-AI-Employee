# Recommendation Architecture

B3 introduces an internal recommendation service that sits on top of the B1 project-health snapshots and B2 change-intelligence findings.

## Inputs

- latest project-health snapshots;
- latest change findings;
- project registry metadata;
- evidence freshness state;
- project sensitivity and release rules.

## Responsibilities

- generate deterministic recommendation candidates;
- score recommendations with a versioned policy;
- attach blockers and dependencies explicitly;
- deduplicate repeated evaluations semantically;
- persist current recommendation state and provenance;
- expose queue and portfolio views for human review.

## Design constraints

- no shell execution;
- no Codex invocation;
- no automatic repository writes;
- no Dashboard execution surface;
- no work-package generation yet.
