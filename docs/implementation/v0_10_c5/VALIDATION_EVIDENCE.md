# Validation Evidence

## Local Checks

Run and pass:

- `python -m pytest tests\test_programme_packages.py`
- `python -m ruff check src\gaia\programme_packages.py src\gaia\service.py src\gaia\db.py tests\test_programme_packages.py`
- `python -m mypy src\gaia\programme_packages.py src\gaia\service.py src\gaia\db.py tests\test_programme_packages.py`

## What the Tests Prove

- deterministic programme-package fingerprinting;
- deterministic insertion-order handling;
- revision-history persistence;
- package grouping from release-train and work-package inputs;
- human-reviewable package state derivation;
- risk and acceptance-criteria aggregation.
