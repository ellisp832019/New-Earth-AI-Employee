# Test Results

## Environment

- Python: `3.14.4`
- Editable install: successful
- Git: available
- SQLite FTS5: available

## Commands run

- `gaia doctor`
- `pytest`
- `ruff check src tests`
- `mypy src\gaia`
- `gaia project scan microgrow-v1`
- `gaia project snapshot microgrow-v1`
- `gaia project report microgrow-v1 --format markdown --output data\reports\MICROGROW_FOUNDATION_REPORT.md`
- `gaia project report microgrow-v1 --format json --output data\reports\MICROGROW_FOUNDATION_REPORT.json`

## Results

- `gaia doctor`: passed
- `pytest`: 28 passed, 1 warning
- `ruff check src tests`: passed
- `mypy src\gaia`: passed
- MicroGrow scan: passed
- MicroGrow snapshot: passed
- Markdown report generation: passed
- JSON report generation: passed

## Notes

- The pytest warning was a Starlette deprecation notice from the test client stack.
- The MicroGrow validation commands completed without modifying the inspected repository.
