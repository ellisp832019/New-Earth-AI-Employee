# Architecture and Dependency UI

## Architecture Registry

The architecture registry page shows:

- entity IDs and identity keys;
- kind;
- status;
- freshness;
- current revision number;
- relationships touching the selected entity;
- revision history when available from the backend payload.

## Dependency Graph

The dependency page shows:

- graph fingerprint;
- node count;
- edge count;
- cycles;
- unresolved findings;
- selected-project dependency projections;
- reverse dependencies.

## Boundary

- no graph recomputation in Dart;
- no graph editing;
- no hidden traversal logic.
