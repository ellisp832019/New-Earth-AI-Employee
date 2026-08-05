# GAIA v0.3 PR Summary

## Title

GAIA v0.3 - Windows Desktop Control Centre

## Purpose

This pull request delivers a standalone Flutter Windows control centre for the existing read-only GAIA backend.

## Highlights

- Windows desktop shell and navigation.
- First-run setup and local settings storage.
- Backend health and compatibility checks.
- Project browsing and read-only MicroGrow emphasis.
- Evidence, snapshots, reports, agent runs and audit views.
- Deterministic conversational workflow with Codex prompt drafting.
- Loopback-only backend startup support.

## Validation

- Python compileall: passed.
- Ruff: passed.
- mypy: passed.
- pytest: passed.
- Flutter analyze: passed.
- Flutter test: passed.
- Windows debug build: passed.
- Windows release build: passed.
- Live smoke test: passed through `flutter run -d windows --release`.

## Boundary Notes

- The PR preserves the read-only MicroGrow boundary.
- The PR does not add a second AI backend for the New Earth Dashboard.
- The PR does not merge into main and does not tag the release.
