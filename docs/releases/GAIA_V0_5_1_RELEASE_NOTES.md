# GAIA v0.5.1 Release Notes

GAIA v0.5.1 is a focused managed-backend and Windows tooling hotfix.

## Fixed

- `$pid` collision in managed-backend PowerShell scripts.
- Safe start, check, stop, and restart behavior for the managed backend.
- Stale PID-file handling.
- UTF-8-safe Flutter/version status output.
- Updated VS Code task wiring for the repaired scripts.

## Compatibility

- The GAIA v1 integration contract is unchanged.
- The v0.5.0 integration client remains compatible.
- Backend version reporting now returns `0.5.1`.

## Validation

- Managed-backend lifecycle validation passes on a clean loopback port.
- Python, Flutter, and workspace validation remain green after the hotfix.
