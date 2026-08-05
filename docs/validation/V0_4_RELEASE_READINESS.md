# GAIA v0.4 Release Readiness

## Scope

- Workspace scaffolding for controlled workflows.
- Local validation wrapper scripts.
- Release-readiness command path.
- Repository safety boundaries for runtime folders.

## Validation Performed

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_vscode_workspace.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release_readiness.ps1`

## Results

- VS Code workspace validation passed.
- Python `compileall` passed.
- Ruff passed.
- mypy passed.
- pytest passed with 49 tests and 1 existing Starlette/httpx deprecation warning.
- Flutter `pub get` completed successfully.
- Flutter analyze passed.
- Flutter test passed.
- Flutter debug build passed.
- Flutter release build passed.
- `git diff --check` completed without content errors.
- The generated Flutter registrant files were reviewed and restored to the current branch baseline because no genuine plugin dependency change was present.
- A live read-only MicroGrow scan, snapshot, deterministic question flow, task creation, draft creation, approval decision, draft revision, and daily brief generation were executed locally.

## Notes

- The generated Flutter registrant files are currently restored to the branch baseline.
- Runtime placeholder directories now exist under `data/` for drafts, approvals, briefs, tasks, integration and runtime state.
