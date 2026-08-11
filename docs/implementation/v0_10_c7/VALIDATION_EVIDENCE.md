# GAIA v0.10 C7A Validation Evidence

## Cross-Repository Acceptance

- GAIA C7A merged main: `3a7d316f66aabf9cd677200c55fd5be05a4d6afe`
- GAIA PR: `#30`
- Dashboard C7B merged main: `67bb0057322ae0d5d7514bdaba5e29258ec3efda`
- Dashboard PR: `#17`
- Dashboard consumed GAIA through the supported integration-client and dashboard-module boundary only.

## CI Repair Note

- GitHub Actions initially failed `python -m mypy src/gaia` with seven type-safety errors in `src/gaia/cli.py`.
- This repair narrowed the CLI payload handling, typed the architecture filters with the canonical domain Literals, and removed the premature C8 handoff file.

## Python

- `python -m ruff check src tests` - PASS
- `python -m mypy src\gaia` - PASS
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
- C7B protected-branch checks passed in the Dashboard repository:
  - Flutter Quality
  - Project Control Validation
  - Windows Release Build
- C7B local validation passed in the Dashboard repository:
  - `flutter analyze`
  - `flutter test` - 561 tests
  - `flutter build windows --release`
  - `project-control validate`
  - `project-control report`
  - `release-readiness`
