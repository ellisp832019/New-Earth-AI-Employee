# ADR: GAIA Consumes NEOS Governance Context

## Status

Accepted for the current feature branch implementation.

## Context

GAIA v0.9 already provides local project registry, change-intelligence, prioritisation, work-package, API, CLI, and brief-generation surfaces.

The new NEOS governance work introduces authoritative observed/reconciled engineering findings. GAIA must not recreate or overwrite that source truth.

## Decision

GAIA will consume NEOS governance through a read-only HTTP contract and treat it as authoritative engineering context.

GAIA will:

- preserve NEOS source fields;
- add separate interpretation and prioritisation;
- build draft work-package previews only;
- expose read-only API/CLI/brief surfaces;
- persist only local consumer cache/history where required.

## Consequences

- Platform Core remains the declared architecture authority.
- NEOS remains the observed/reconciled engineering authority.
- GAIA remains downstream and does not become a second architecture registry.
- Cached governance snapshots are explicitly local and must not be presented as live NEOS truth.

## Notes

This ADR applies to the live GAIA implementation and documentation for the governance context feature. It does not alter historical release notes.
