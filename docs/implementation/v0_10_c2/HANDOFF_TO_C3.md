# Handoff to C3

Proceed to C3 only after:

1. the C2 tests pass;
2. the graph output is deterministic across rebuilds;
3. the branch is clean and pushed;
4. the C2 pull request is open;
5. no Dashboard or MicroGrow changes are present.

## C2 Output

- canonical dependency graph builder;
- direct/transitive/reverse dependency queries;
- cycle detection;
- shared dependency detection;
- orphan detection;
- unresolved dependency findings.

## C3 Preconditions

- change-impact intelligence can consume the canonical graph;
- no new registry storage is needed for C2;
- release version remains `0.9.0`.
