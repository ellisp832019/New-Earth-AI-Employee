# Handoff to C2

Proceed to C2 only after:

1. the C1 tests pass;
2. the database migration path is validated;
3. the branch is clean and pushed;
4. the C1 pull request is open;
5. no Dashboard or MicroGrow changes are present.

## C1 Output

- canonical project contract storage;
- canonical architecture registry storage;
- deterministic revision history;
- schema migration to `Database.SCHEMA_VERSION = 12`.

## C2 Preconditions

- the dependency graph can consume the registry read models;
- no schema regressions are visible in the existing v0.9 surfaces;
- release version remains `0.9.0`.
