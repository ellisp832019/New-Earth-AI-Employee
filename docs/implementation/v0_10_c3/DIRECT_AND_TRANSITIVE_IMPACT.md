# Direct and Transitive Impact

## Direct Impact

Direct impact is computed from the resolved target itself and from its immediate dependents in the dependency graph.

Examples:

- changed API or package target -> direct consumers are affected;
- changed project contract -> the owning project and its direct consumers are affected;
- changed shared library -> direct consuming projects are affected.

## Transitive Impact

Transitive impact uses the canonical C2 traversal.

Requirements:

- stable ordering;
- cycle safety;
- provenance preservation;
- path preservation;
- no invented nodes;
- no undocumented dependency inference.

## Reason Codes

Reason codes are canonical and structured.

Examples:

- `TARGET_ENTITY`
- `TARGET_PROJECT`
- `DIRECT_CONSUMER`
- `TRANSITIVE_DEPENDENT`
- `SHARED_DEPENDENCY`
- `CONTRACT_CONSUMER`
- `SCHEMA_CONSUMER`
- `RELEASE_COUPLING`
- `BLOCKED_BY_UNRESOLVED_DEPENDENCY`

## Project Projection

Entity impacts collapse into project impacts while preserving:

- supporting entities;
- supporting edges;
- paths;
- provenance;
- freshness;
- trust.
