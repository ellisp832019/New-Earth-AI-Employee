# Validation Evidence

## Local Checks

Run and pass:

- `python -m pytest tests\test_programme_intelligence.py`
- `python -m ruff check src\gaia\programme_intelligence.py src\gaia\service.py tests\test_programme_intelligence.py`
- `python -m mypy src\gaia\programme_intelligence.py src\gaia\service.py tests\test_programme_intelligence.py`

## What the Tests Prove

- deterministic roadmap fingerprinting;
- deterministic release-train fingerprinting;
- insertion-order stability;
- dependency-order derivation;
- participant-order derivation;
- release-readiness aggregation;
- deterministic roadmap and release-train classification from canonical inputs.
