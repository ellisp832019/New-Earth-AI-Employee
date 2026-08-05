# Package Validation

Package version: `0.1.0`

## Validation completed before packaging

- Python source compilation: passed.
- Automated tests: 20 passed.
- Test coverage: 70% overall in the packaging environment.
- CLI help invocation: passed.
- API tests: passed.
- Complete temporary-repository scan/snapshot/report workflow: passed.
- Read-only integrity test: passed.

## Packaging environment

The automated validation bundled with this repository was originally run in a Linux container using Python 3.13.5. This Windows validation pass was run on Python 3.14.4 because no Python 3.11 or 3.12 interpreter was installed on the machine. The package metadata and setup script were updated so the editable install succeeds in that environment.

## Not validated here

The actual `D:\Dev\Projects\MicroGrow V1` repository and Windows PowerShell scripts were not available inside the packaging environment. The included Codex prompt instructs Codex to perform the full Windows and real-MicroGrow validation and create evidence documents.

Static lint and mypy tools were declared in the development dependencies but were not available from the isolated package index used during packaging. Codex must run them during the Windows validation workflow.
