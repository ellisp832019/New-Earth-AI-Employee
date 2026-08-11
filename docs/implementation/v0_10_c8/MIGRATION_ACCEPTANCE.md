# Migration Acceptance

## Evidence

- `python -m pytest -q tests/test_workflows.py::test_database_migration_preserves_existing_data tests/test_dependency_graph.py::test_dependency_graph_rebuilds_identically_after_restart`: passed
- `python -m pytest`: passed, `134` tests

## Acceptance Notes

- existing v0.9 data opens successfully;
- schema migrations remain deterministic;
- existing project officer data survives restart;
- programme registry data survives restart;
- architecture registry revisions remain deterministic;
- dependency graph rebuilds identically after restart;
- no destructive migration was observed.
