# GAIA v0.9.0 Validation Evidence

## Backend

- `py -3.14 -m ruff check src tests`: passed
- `py -3.14 -m mypy src\gaia`: passed
- `py -3.14 -m pytest`: passed, `106` tests

## Windows

- `flutter analyze` in `apps\gaia_windows`: passed
- `flutter test` in `apps\gaia_windows`: passed, `8` widget tests
- `flutter build windows --release` in `apps\gaia_windows`: passed
- live smoke via `scripts\test_gaia_windows_live.ps1`: passed, backend `0.9.0`, app stayed running, no stderr

## Repository scripts

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\export_openapi_contract.ps1 -PythonPath '.\.venv\Scripts\python.exe'`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_integration_contract.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_dashboard_conformance.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release_readiness.ps1`: passed

## Release artifact

- `gaia_windows.exe` SHA-256: `B97E89EA6151C2C9D909B9FC687F5C53AAFFEC10709F2061DD14004BDE406FEB`

## External read-only proof

- Dashboard status, HEAD, and origin/main were captured read-only.
- MicroGrow status and HEAD were captured read-only.

## Notes

- No build outputs, executables, runtime databases, caches, or `.dart_tool` directories were committed.
