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
- `git grep -n "D:\\Dev\\Projects"`
- `git grep -n "MicroGrow V1" tests`
- `python -m pytest tests\test_agent_v2.py::test_conversational_run_is_read_only`
- `python -m pytest tests\test_security.py::test_rejects_nested_traversal`
- `python -m pytest tests\test_security.py::test_rejects_nested_traversal_missing_component`
- `python -m pytest tests\test_security.py::test_allows_mixed_separators_portable`
- `python -m pytest tests\test_security.py::test_allows_mixed_separators_and_case_windows`
- `gaia models status`
- `gaia ask microgrow-v1 "What was completed most recently?" --deterministic-only`
- `gaia agent runs list`

## Results

- `python -m compileall src tests`: passed
- `python -m ruff check src tests`: passed
- `python -m mypy src\gaia`: passed
- `python -m pytest`: 40 passed, 1 warning
- `gaia doctor`: passed
- `git grep -n "D:\\Dev\\Projects"`: passed
- `git grep -n "MicroGrow V1" tests`: passed
- `python -m pytest tests\test_agent_v2.py::test_conversational_run_is_read_only`: passed
- `python -m pytest tests\test_security.py::test_rejects_nested_traversal`: passed
- `python -m pytest tests\test_security.py::test_rejects_nested_traversal_missing_component`: passed
- `python -m pytest tests\test_security.py::test_allows_mixed_separators_portable`: passed
- `python -m pytest tests\test_security.py::test_allows_mixed_separators_and_case_windows`: passed
- `gaia models status`: passed
- `gaia ask microgrow-v1 "What was completed most recently?" --deterministic-only`: passed
- `gaia agent runs list`: passed

## Notes

- The pytest warning was the existing Starlette deprecation notice from the test client stack.
- The deterministic ask command created a stored agent run in the local GAIA database for `microgrow-v1`.
- The release hardening pass added regression coverage for prompt-injection warning separation and project-relative Git evidence paths.
- The CI portability repair moved the read-only conversational regression onto a temporary Git repository fixture.
- The package version source was corrected to `0.2.0`.
- The local SQLite database and generated reports remain excluded by `.gitignore`.
