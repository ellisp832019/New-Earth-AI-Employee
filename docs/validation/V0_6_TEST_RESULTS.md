# GAIA v0.6 Test Results

Recorded during the closeout pass.

## CI repair note

- The first GitHub Actions `windows_validation` run failed at `Export OpenAPI contract` because the script assumed a repository `.venv` on the clean runner.
- The portability repair added a shared Windows Python resolver that prefers `.venv`, accepts `-PythonPath`, honors `GAIA_PYTHON`, and falls back to `python` on PATH.
- The repaired resolver was verified locally in default, explicit-path, and PATH-based modes.
- A follow-up CI-only parser hardening was required in `scripts/version_status.ps1` because GitHub's `flutter --version --machine` output can include a `Resolving...` preamble before the JSON payload.

## Passed

- Python compileall on `src` and `tests`
- Python Ruff on `src` and `tests`
- Python mypy on `src/gaia`
- Python pytest suite
- Flutter Windows app analyze and test
- Dart integration client analyze and test
- Dashboard module analyze and test
- Example dashboard host analyze and test
- v0.6 validation scripts
- OpenAPI contract export on the local `.venv` and explicit interpreter paths

## Pending

- no pending local functional failures at the time of this note
