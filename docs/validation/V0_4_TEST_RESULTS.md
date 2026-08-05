# GAIA v0.4 Test Results

## Python

- `python -m compileall src tests`: passed
- `python -m ruff check src tests`: passed
- `python -m mypy src\gaia`: passed
- `python -m pytest`: 49 passed, 1 warning

## Flutter

- `flutter pub get`: passed
- `flutter analyze`: passed
- `flutter test`: passed
- `flutter build windows --debug`: passed
- `flutter build windows --release`: passed

## Workspace Validation

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_vscode_workspace.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_v0_4_validation.ps1`: passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release_readiness.ps1`: passed

## Live Workflow Evidence

- MicroGrow scan: passed
- MicroGrow snapshot: passed
- Deterministic ask: passed
- Task-from-run creation: passed
- Codex draft creation and labeling: passed
- Approval creation and approval-for-manual-use decision: passed
- Draft invalidation after revision: passed
- Daily brief generation: passed

## Warning

- One existing Starlette/httpx deprecation warning remains in the test client stack.
