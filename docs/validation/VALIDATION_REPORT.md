# Validation Report

GAIA v0.1 was validated on `D:\Dev\Projects\New-Earth-AI-Employee` against the read-only MicroGrow project at `D:\Dev\Projects\MicroGrow V1`.

## Environment

- Git: available
- Python: `3.14.4`
- SQLite FTS5: available
- GAIA branch: `gaia-v0.1`

## Build and setup

- `scripts\setup_windows.ps1` completed successfully with the local Python 3.14.4 interpreter.
- Editable install succeeded after the package metadata was updated to allow the local compatible interpreter.

## Automated verification

- `gaia doctor`: passed
- `pytest`: 28 passed, 1 warning
- `ruff check src tests`: passed
- `mypy src\gaia`: passed

## Real MicroGrow validation

- Pre-scan branch: `planning/microgrow-v1-firmware-target-dependency-lock`
- Pre-scan SHA: `0f9df32862bfb74f0acba8c4c1aa84d5a17c8363`
- Pre-scan status: clean
- Scan result: 1743 documents discovered, 1741 indexed, 2 skipped, 0 failed
- Snapshot ID: `4e9f3617-7517-420b-a15b-8c7c5624f5f8`
- Markdown report: `data\reports\MICROGROW_FOUNDATION_REPORT.md`
- JSON report: `data\reports\MICROGROW_FOUNDATION_REPORT.json`

## Search validation

All requested searches returned results:

- `PlatformIO build verification`: 5 results
- `release readiness`: 5 results
- `experimental`: 5 results
- `future version`: 5 results
- `user guide`: 5 results

## Audit review

Audit events were inspected after scan, snapshot, report and search activity. The metadata remained limited to safe values such as counts, snapshot IDs and report format. No document contents, secrets or credentials appeared in the audit metadata.

## Read-only proof

The MicroGrow branch, commit and porcelain status were captured before validation and again afterwards. They matched exactly, so the GAIA scan and report workflow did not modify the inspected repository.

## Limitations

- The machine did not have Python 3.11 or 3.12 installed, so validation used Python 3.14.4.
- The pytest run produced one Starlette deprecation warning from the bundled test client stack.
