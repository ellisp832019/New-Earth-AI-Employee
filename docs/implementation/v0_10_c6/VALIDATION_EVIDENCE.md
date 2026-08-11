# Validation Evidence

## Python

- `.\.venv\Scripts\python.exe -m ruff check src tests` - passed
- `.\.venv\Scripts\python.exe -m mypy src\gaia` - passed
- `.\.venv\Scripts\python.exe -m pytest` - passed, `121` tests

## Flutter / Windows App

- `flutter analyze` in `apps/gaia_windows` - passed
- `flutter test` in `apps/gaia_windows` - passed
- `flutter build windows --release` in `apps/gaia_windows` - passed

## Repository Scripts

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_integration_contract.ps1` - passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_dashboard_conformance.ps1` - passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release_readiness.ps1` - passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test_gaia_windows_live.ps1` - passed

## Final Live Windows Validation

- `backendHealthy = true`;
- `backendVersion = 0.9.0`;
- `backendStatus = ok`;
- `backendPid = 34412`;
- `appPid = 10944`;
- `appRunning = true`;
- `appExitCode = null`;
- `appStderrTail = empty`;
- final live validation result: `PASS`.

## Windows Soak Acceptance

- release executable used;
- managed GAIA backend was started and healthy before the final connected application launch;
- soak duration was `00:10:00.1552832`;
- soak start: `11/08/2026 12:56:32`;
- soak end: `11/08/2026 13:06:32`;
- soak process PID: `28076`;
- process-level result: `PASS` - GAIA remained running for the entire soak;
- the Programme Intelligence workspace was exercised during the soak.

## Notes

- dashboard repository remained unchanged;
- MicroGrow repository remained unchanged;
- the workspace route is internal and hidden from the public OpenAPI schema.
- stdout contained dependency-maintenance notices only:
  - `flutter_markdown 0.7.7+1` is discontinued and replaced by `flutter_markdown_plus`;
  - five packages have newer versions incompatible with current dependency constraints;
- these dependency-maintenance notices are non-blocking observations;
- do not upgrade dependencies in this PR.
