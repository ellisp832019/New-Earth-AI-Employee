# Release Validation Evidence

## Backend

- `py -3.14 -m ruff check src tests`: passed
- `py -3.14 -m mypy src\gaia`: passed
- `py -3.14 -m pytest`: passed, `106` tests

## Windows App

- `flutter analyze`: passed
- `flutter test`: passed, `8` widget tests
- `flutter build windows --release`: passed

## Repository Scripts

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/export_openapi_contract.ps1 -PythonPath '.\.venv\Scripts\python.exe'`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate_integration_contract.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate_dashboard_conformance.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release_readiness.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_gaia_windows_live.ps1`: passed

## Package Validation

- `packages/gaia_integration_client`: analyze and tests passed
- `packages/gaia_dashboard_module`: analyze and tests passed
- `examples/gaia_dashboard_host`: analyze and tests passed

