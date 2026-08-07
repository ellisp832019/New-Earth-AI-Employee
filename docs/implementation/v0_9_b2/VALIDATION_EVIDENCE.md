# Validation Evidence

Validation was run after the B2 implementation landed.

## Checks

- `ruff check src tests`
- `mypy src\gaia`
- `pytest`
- `scripts\release_readiness.ps1`
- `scripts\validate_dashboard_conformance.ps1`
- `scripts\validate_integration_contract.ps1`

## Coverage

- snapshot comparison and noise filtering;
- branch, HEAD, working-tree, upstream, and important-path drift;
- health transition and configuration drift;
- stale evidence handling;
- comparison and finding persistence;
- migration from schema version 8 to 9;
- read-only compatibility with the released v0.8 Dashboard contract.

## Results

- `pytest`: 90 passed, 1 warning;
- warning: `StarletteDeprecationWarning` from `fastapi.testclient` via `httpx`;
- release readiness: passed;
- dashboard conformance: passed;
- integration contract: passed;
- Flutter validation scripts emitted dependency advisory messages but did not fail.
