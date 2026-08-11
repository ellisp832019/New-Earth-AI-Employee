# Validation Evidence

## Backend

- `python -m compileall src tests`: passed
- `python -m ruff check src tests`: passed
- `python -m mypy src\gaia`: passed
- `python -m pytest`: passed, `134` tests
- `python -m pytest -q tests/test_workflows.py::test_database_migration_preserves_existing_data tests/test_dependency_graph.py::test_dependency_graph_rebuilds_identically_after_restart`: passed

## Integration Client

- `dart pub get` in `packages/gaia_integration_client`: passed
- `dart test` in `packages/gaia_integration_client`: passed, `3` tests

## Dashboard Module

- `flutter pub get` in `packages/gaia_dashboard_module`: passed
- `flutter analyze` in `packages/gaia_dashboard_module`: passed
- `flutter test` in `packages/gaia_dashboard_module`: passed, `14` tests

## Example Host

- `flutter pub get` in `examples/gaia_dashboard_host`: passed
- `flutter analyze` in `examples/gaia_dashboard_host`: passed
- `flutter test` in `examples/gaia_dashboard_host`: passed, `1` test

## Windows App

- `flutter pub get` in `apps/gaia_windows`: passed
- `flutter analyze` in `apps/gaia_windows`: passed
- `flutter test` in `apps/gaia_windows`: passed, `11` tests
- `flutter build windows --release` in `apps/gaia_windows`: passed after stopping a stale `gaia_windows` process that was locking the release executable

## Contract and Release Scripts

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\export_openapi_contract.ps1 -PythonPath .\.venv\Scripts\python.exe`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_integration_contract.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_dashboard_conformance.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release_readiness.ps1`: passed

## Maintenance Warnings

- `flutter_markdown 0.7.7+1` remains discontinued and replaced by `flutter_markdown_plus`
- several packages report newer versions that are incompatible with the current constraints

## Versioning

- old VERSION: `0.9.0`
- new VERSION: `0.10.0`
- GAIA C7A contract SHA: `3a7d316f66aabf9cd677200c55fd5be05a4d6afe`
- Dashboard accepted main SHA: `67bb0057322ae0d5d7514bdaba5e29258ec3efda`
