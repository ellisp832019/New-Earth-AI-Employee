# Validation Evidence

This file records validation for the B7A dashboard summary expansion.

## Python validation

- `.\.venv\Scripts\python.exe -m ruff check src tests`: passed
- `.\.venv\Scripts\python.exe -m mypy src\gaia`: passed
- `.\.venv\Scripts\python.exe -m pytest`: passed, `106` tests

## Integration client validation

- `dart analyze` in `packages\gaia_integration_client`: passed
- `dart test` in `packages\gaia_integration_client`: passed, `2` tests

## Dashboard module validation

- `flutter pub get` in `packages\gaia_dashboard_module`: passed
- `flutter analyze` in `packages\gaia_dashboard_module`: passed
- `flutter test` in `packages\gaia_dashboard_module`: passed, including the new B7 controller and widget tests

## Example host validation

- `flutter pub get` in `examples\gaia_dashboard_host`: passed
- `flutter analyze` in `examples\gaia_dashboard_host`: passed
- `flutter test` in `examples\gaia_dashboard_host`: passed, `1` test

## Repository conformance validation

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_dashboard_conformance.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_integration_contract.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release_readiness.ps1`: passed

## Read-only external proof

- `git -C "D:\Dev\Projects\MicroGrow V1" status --short --branch`: captured, no local writes
- `git -C "D:\Dev\Projects\MicroGrow V1" rev-parse HEAD`: captured, no local writes
- `git -C "D:\Dev\Projects\New Earth - Command Dashboard" status --short --branch`: captured, no local writes
- `git -C "D:\Dev\Projects\New Earth - Command Dashboard" rev-parse HEAD`: captured, no local writes

## Notes

- validation was run sequentially
- failures were fixed before merge
- no build artifacts are committed
