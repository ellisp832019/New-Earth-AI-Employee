# Project Health Model

The health model captures a deterministic snapshot of each registered project.

## Snapshot contents

- project identity and canonical root;
- project configuration fingerprint;
- normalized health status;
- reason codes and explanations;
- blocking, attention, and unknown condition lists;
- evidence references;
- serialized normalized payload;
- provenance and audit linkage;
- content fingerprint for repeatability.

## Portfolio view

The portfolio view aggregates the latest health snapshot for each enabled project and reports:

- per-project status;
- snapshot counts;
- latest snapshot identifiers;
- projects that have no recorded health snapshot yet;
- counts by normalized status.
