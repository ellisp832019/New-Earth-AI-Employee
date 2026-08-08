# Validation Evidence

## Local Checks

Run and pass:

- `python -m ruff check src tests`
- `python -m mypy src\gaia`
- `python -m pytest`
- `powershell -ExecutionPolicy Bypass -File .\scripts\validate_integration_contract.ps1`
- `powershell -ExecutionPolicy Bypass -File .\scripts\validate_dashboard_conformance.ps1`
- `powershell -ExecutionPolicy Bypass -File .\scripts\release_readiness.ps1`

## What the Tests Prove

- deterministic proposal fingerprinting;
- deterministic impact fingerprinting;
- insertion-order stability;
- restart stability;
- fail-closed unknown targets;
- project projection from entity impacts;
- contract and release impact handling;
- work-package projection without mutation;
- validation reference extraction without execution;
- structural risk and sequencing derivation.
