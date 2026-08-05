# GAIA v0.3.0 Release Notes

GAIA v0.3.0 introduces a Windows desktop control centre for the existing read-only GAIA backend.

## What changed

- Added `apps/gaia_windows`, a Flutter Windows client for local-first project inspection.
- Added first-run setup, backend connection management, and local settings storage.
- Added read-only screens for projects, evidence, snapshots, reports, agent runs, and audit events.
- Added a prompt-drafting view for the existing conversational workflow.
- Added Windows setup, launch, test, build, and validation scripts.
- Added v0.3 validation and build proof docs.

## Safety boundary

- The desktop app does not add write capability for MicroGrow.
- The app only consumes existing read-only backend APIs.
- The control centre remains local-first and loopback-scoped.

## Verification

- Flutter analyze: passed
- Flutter test: passed
- Windows debug build: passed
- Windows release build: passed
- Python compileall, ruff, mypy and pytest: passed
