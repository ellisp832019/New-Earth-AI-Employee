# Validation Evidence

## Python

- `.\.venv\Scripts\python.exe -m ruff check src tests` - passed
- `.\.venv\Scripts\python.exe -m mypy src\gaia` - passed
- `.\.venv\Scripts\python.exe -m pytest` - passed, `121` tests

## Flutter / Windows App

- `flutter analyze` in `apps/gaia_windows` - passed
- `flutter test` in `apps/gaia_windows` - passed
- `flutter build windows --release` in `apps/gaia_windows` - passed

## Repository Scripts

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_integration_contract.ps1` - passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_dashboard_conformance.ps1` - passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release_readiness.ps1` - passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test_gaia_windows_live.ps1` - passed

## Notes

- dashboard repository remained unchanged;
- MicroGrow repository remained unchanged;
- the workspace route is internal and hidden from the public OpenAPI schema.
