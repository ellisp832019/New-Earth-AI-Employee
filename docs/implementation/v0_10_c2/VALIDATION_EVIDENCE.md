# Validation Evidence

## Checks to Run

- `python -m ruff check src tests`
- `python -m mypy src\gaia`
- `python -m pytest`
- `powershell -ExecutionPolicy Bypass -File .\scripts\validate_integration_contract.ps1`
- `powershell -ExecutionPolicy Bypass -File .\scripts\validate_dashboard_conformance.ps1`
- `powershell -ExecutionPolicy Bypass -File .\scripts\release_readiness.ps1`

## Expected Outcomes

- graph fingerprint stays stable across rebuilds;
- project-level projection stays deterministic;
- cycle and shared dependency output stays canonical;
- unresolved dependency declarations remain visible as findings;
- VERSION remains `0.9.0`.
