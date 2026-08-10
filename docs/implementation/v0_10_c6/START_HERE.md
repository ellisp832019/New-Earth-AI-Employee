# C6 Start Here

GAIA v0.10 C6 adds the Windows Programme Intelligence workspace inside the existing GAIA Windows Control Centre.

## What Changed

- added a dedicated Programme Intelligence workspace to the Windows app;
- kept the existing Project Officer workspace intact;
- added an internal, non-public backend workspace payload for the Windows app;
- kept Canonical programme logic in Python/backend services;
- kept `VERSION` at `0.9.0`.

## Workspace Surfaces

- Programme Overview;
- Architecture Registry;
- Dependency Graph;
- Impact Analysis;
- Change Proposals;
- Programme Roadmap;
- Release Trains;
- Programme Packages;
- Decisions;
- Cross-Project Evidence.

## Safety Boundaries

- no Codex execution path;
- no shell or Git execution path from the workspace;
- no repository mutation path from the workspace;
- no direct SQLite access from Flutter;
- no Dashboard mutation;
- no MicroGrow mutation;
- no release publication or tagging.

## Validation Summary

- Python lint, mypy, and pytest passed;
- Flutter analyze, flutter test, and flutter release build passed;
- integration contract, dashboard conformance, and release readiness scripts passed;
- live Windows validation passed.

## Handoff

See `HANDOFF_TO_C7.md` for the next phase boundary.
