# GAIA v0.4 Pull Request Summary

## Title

GAIA v0.4 - Controlled Tasks, Drafts and Approval Foundation

## Summary

This pull request adds a controlled local workflow foundation to GAIA:

- task records and task history;
- draft records and revisions;
- approval records and decisions;
- deterministic daily brief generation;
- CLI and FastAPI endpoints for the new records;
- Flutter Windows screens for tasks, drafts, approvals, briefs, and VS Code operations;
- release and validation documentation.

## Security Boundaries

- MicroGrow remains read-only.
- Drafts are labelled `DRAFT - NOT EXECUTED`.
- Approvals are manual-use decisions only.
- No execution endpoint was added.
- No arbitrary filesystem or shell execution was added.

## Validation

- `python -m compileall src tests`
- `python -m ruff check src tests`
- `python -m mypy src\gaia`
- `python -m pytest`
- `flutter pub get`
- `flutter analyze`
- `flutter test`
- `flutter build windows --debug`
- `flutter build windows --release`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_vscode_workspace.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_v0_4_validation.ps1`

## Live Read-Only Proof

The local GAIA workflow was exercised against MicroGrow with a scan, snapshot, deterministic questions, task creation, draft creation, approval creation, approval invalidation on draft revision, and daily brief generation.

MicroGrow branch, SHA, and porcelain status remained unchanged.

## Manual Review Notes

- Confirm the Windows desktop screens in the local app if a final manual GUI pass is required.
- Confirm the release branch and PR are ready for merge review.
