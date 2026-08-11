# GAIA v0.10 C7A Validation Evidence

## Python

- `python -m ruff check src tests` - PASS
- `python -m pytest` - PASS, `134 passed in 235.86s`

## Dart Integration Client

- `dart analyze` in `packages/gaia_integration_client` - PASS
- `dart test` in `packages/gaia_integration_client` - PASS

## Dashboard Module

- `flutter analyze` in `packages/gaia_dashboard_module` - PASS
- `flutter test` in `packages/gaia_dashboard_module` - PASS

## OpenAPI Contract

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_openapi_contract.ps1 -PythonPath .\.venv\Scripts\python.exe`
- result: `contracts/openapi/gaia-v1.json` regenerated successfully

## Notes

- the public programme read surfaces are present and covered by tests;
- the dashboard module now renders a read-only programme summary view;
- the contract export is intentionally tracked because the public API surface changed.
