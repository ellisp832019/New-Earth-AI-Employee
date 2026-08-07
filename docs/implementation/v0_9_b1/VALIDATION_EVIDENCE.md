# Validation Evidence

Validation was run after the B1 implementation landed.

## Checks

- `ruff check src tests`
- `mypy src\gaia`
- `pytest`
- `scripts\release_readiness.ps1`
- `scripts\validate_dashboard_conformance.ps1`
- `scripts\validate_integration_contract.ps1`

## What the checks covered

- registry loading and duplicate-root rejection;
- Git state inspection with the new upstream and dirty-tree fields;
- project-health capture, persistence, and portfolio aggregation;
- schema migration from version 7 to version 8;
- public API stability for the project list endpoint.
