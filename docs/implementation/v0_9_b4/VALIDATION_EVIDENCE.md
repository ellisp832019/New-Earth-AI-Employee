# Validation Evidence

The B4 implementation should be validated with the repository-owned checks.

## Core checks

- `python -m pytest tests/test_recommendations.py`
- `python -m pytest`
- `python -m ruff check src tests`
- `python -m mypy src\gaia`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release_readiness.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_dashboard_conformance.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_integration_contract.ps1`

## Evidence to capture

- successful test output;
- schema migration result;
- prompt rendering result;
- approval and handoff state transitions;
- staleness detection behavior.
