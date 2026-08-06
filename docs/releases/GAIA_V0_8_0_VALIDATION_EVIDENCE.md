# GAIA v0.8.0 Validation Evidence

## Backend Validation

- Command: `.\.venv\Scripts\python.exe -m ruff check src tests`
- Result: passed
- Command: `.\.venv\Scripts\python.exe -m mypy src\gaia`
- Result: passed, `Success: no issues found in 21 source files`
- Command: `.\.venv\Scripts\python.exe -m pytest`
- Result: passed, `70 passed, 1 warning`

## Official Package Validation

### `packages/gaia_integration_client`

- Command: `dart pub get`
- Command: `dart analyze`
- Command: `dart test`
- Result: passed

### `packages/gaia_dashboard_module`

- Command: `flutter pub get`
- Command: `flutter analyze`
- Command: `flutter test`
- Result: passed

### `examples/gaia_dashboard_host`

- Command: `flutter pub get`
- Command: `flutter analyze`
- Command: `flutter test`
- Result: passed

## Repository Script Validation

- Command: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_openapi_contract.ps1 -PythonPath '.\.venv\Scripts\python.exe'`
- Result: passed, OpenAPI contract exported to `contracts/openapi/gaia-v1.json`
- Command: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_dashboard_conformance.ps1`
- Result: passed
- Command: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release_readiness.ps1`
- Result: passed

## Dashboard Acceptance Evidence

- Dashboard GAIA employee screen test passed.
- Dashboard More screen GAIA tile test passed.
- Dashboard settings repository GAIA flag test passed.
- Dashboard Windows startup repair and analyzer repair were verified in PR #4.
- Dashboard executable SHA-256 from the accepted Windows release build:
  - `BD53BBC02E82F10D84D33CF25A74D9FB0CB56528DDCA5F5F710338309052C210`

## MicroGrow Read-Only Proof

- Branch: `planning/microgrow-v1-firmware-target-dependency-lock`
- SHA: `0f9df32862bfb74f0acba8c4c1aa84d5a17c8363`
- Read-only commands confirmed no change in branch, HEAD, or diff state.
