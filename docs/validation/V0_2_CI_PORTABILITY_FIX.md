# GAIA v0.2 CI Portability Fix

## Failing CI Run

GitHub Actions initially reported `3 failed, 35 passed, 1 warning` on the Python 3.11 and Python 3.14 jobs.

## Root Causes

1. The conversational read-only regression test loaded Peter's Windows-only MicroGrow path and failed on Ubuntu.
2. The security path test assumed Windows case-insensitive path semantics on Linux.
3. Nested traversal requests could surface `FileNotFoundError` before GAIA converted them into the public `PathSecurityError`.

## Corrections

- Replaced the CI conversational read-only test with a temporary Git repository fixture and temporary GAIA project configuration.
- Split the security path tests into a Windows-specific mixed-separator/case test and a portable Linux-safe backslash test.
- Hardened `resolve_project_path` so traversal and malformed or unreachable requested paths fail closed with `PathSecurityError`.
- Corrected the package version to `0.2.0`.
- Updated the CI trigger policy to `pull_request` targeting `main`, `push` to `main`, and `workflow_dispatch`.

## Windows-Specific Testing

- Windows-only mixed-separator and case-folding behavior remains validated on Windows runners.
- The separate local Windows validation lane still documents the real MicroGrow read-only proof.

## Linux CI Testing

- The conversational read-only test now uses only a temporary Git repository.
- The portable path-security test uses a backslash separator without assuming Linux case-insensitive filesystem behavior.
- GitHub Actions does not require Peter's MicroGrow repository, Ollama, cloud services, or credentials.

## Package Version

- Project version source corrected to `0.2.0` in `pyproject.toml` and `src/gaia/__init__.py`.

## Local Validation

- `compileall`: passed
- Ruff: passed
- mypy: passed
- pytest: passed locally after the portability repair
- `gaia doctor`: passed locally

## GitHub Actions Result

Pending after the branch push and PR re-run.
