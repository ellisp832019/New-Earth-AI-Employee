# Validation Evidence

## Checks to Run

- `python -m ruff check src tests`
- `python -m mypy src\gaia`
- `python -m pytest`
- `scripts\validate_integration_contract.ps1`
- `scripts\validate_dashboard_conformance.ps1`
- `scripts\release_readiness.ps1`

## Expected Outcomes

- schema version advances to `12`;
- v0.9 data remains readable after migration;
- project contract bootstrap remains deterministic;
- architecture entities and relationships bootstrap deterministically;
- existing v0.9 release metadata remains `0.9.0`.
