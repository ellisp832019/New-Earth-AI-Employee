# GAIA v0.2 Test Results

## Environment

- Python: `3.14.4`
- Editable install: successful
- Git: available
- SQLite FTS5: available

## Commands run

- `python -m compileall src tests`
- `python -m ruff check src tests`
- `python -m mypy src\gaia`
- `python -m pytest`
- `gaia doctor`
- `gaia models status`
- `gaia ask microgrow-v1 "What was completed most recently?" --deterministic-only`
- `gaia agent runs list`

## Results

- `python -m compileall src tests`: passed
- `python -m ruff check src tests`: passed
- `python -m mypy src\gaia`: passed
- `python -m pytest`: 38 passed, 1 warning
- `gaia doctor`: passed
- `gaia models status`: passed
- `gaia ask microgrow-v1 "What was completed most recently?" --deterministic-only`: passed
- `gaia agent runs list`: passed

## Notes

- The pytest warning was the existing Starlette deprecation notice from the test client stack.
- The deterministic ask command created a stored agent run in the local GAIA database for `microgrow-v1`.
- The release hardening pass added regression coverage for prompt-injection warning separation and project-relative Git evidence paths.
- The local SQLite database and generated reports remain excluded by `.gitignore`.
