# GAIA v0.10 C3 - Change Impact Intelligence

## Scope

This phase adds deterministic pre-change impact intelligence only.

It answers, without executing the change:

- what architecture entities are directly affected;
- what projects are directly affected;
- what entities and projects are transitively affected;
- which contracts, releases, work packages, and validation references are implicated;
- which evidence should be refreshed;
- which structural risks and sequencing constraints follow from canonical dependency structure;
- which impacts remain unknown or unverified.

## What Was Used

- current approved project contracts from C1;
- architecture entities and relationships from C1;
- the deterministic dependency graph from C2;
- work-package records already present in the repository;
- canonical provenance, freshness, and trust semantics.

## What Was Not Added

- no new public API surface;
- no CLI surface;
- no Dashboard mutation;
- no MicroGrow mutation;
- no release-train logic;
- no programme-package logic;
- no schema bump;
- no persistent impact store.

## Implementation Entry Point

- `src/gaia/change_impact.py`
- `src/gaia/service.py`

## Validation

See [VALIDATION_EVIDENCE.md](VALIDATION_EVIDENCE.md).

## Next Phase

The next phase may consume the canonical proposal and impact result models defined here, but it must not assume any roadmap or release-train behavior.
