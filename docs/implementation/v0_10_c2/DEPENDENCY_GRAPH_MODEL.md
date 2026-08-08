# Dependency Graph Model

## Inclusion Rule

- The graph is derived from the current approved project contracts and current approved architecture registry records.
- Historical revisions remain queryable evidence but do not create duplicate current graph nodes or edges.
- Project contract dependency declarations are resolved only against canonical C1 project and architecture identities.
- Unresolved declarations remain findings.

## Graph Shape

- nodes reference canonical architecture entities;
- edges reference canonical architecture relationships or canonical contract declarations;
- project-level dependency projection is derived from the entity graph, not manually authored.

## Determinism Rule

- identical approved C1 inputs produce identical nodes, edges, findings, ordering, and graph fingerprint;
- insertion order and restart order do not alter the canonical graph.

## Boundary

- the graph is read only;
- no LLM authorship;
- no C3 impact scoring.
