# GAIA v0.10 C4 - Programme Roadmap and Release Train Intelligence

## Scope

This phase adds deterministic programme-level intelligence for:

- roadmap surfacing from canonical project, dependency, recommendation, work-package, and change-impact inputs;
- release-train discovery and participant ordering;
- release readiness aggregation;
- compatibility and rollback relationships;
- validation-reference aggregation;
- deterministic fingerprints for roadmap and release-train outputs.

## What Was Used

- approved project contracts from C1;
- the dependency graph from C2;
- change-impact results from C3;
- project health, recommendation, and work-package evidence already present in the repository.

## What Was Not Added

- no new public API surface;
- no CLI surface;
- no Dashboard mutation;
- no MicroGrow mutation;
- no version bump;
- no schema bump;
- no persistent programme-intelligence store.

## Implementation Entry Point

- `src/gaia/programme_intelligence.py`
- `src/gaia/service.py`

## Validation

See [VALIDATION_EVIDENCE.md](VALIDATION_EVIDENCE.md).

## Next Phase

The next phase may consume these roadmap and release-train outputs to build human-reviewable programme packages, but it should not reimplement the underlying scoring or dependency analysis.
