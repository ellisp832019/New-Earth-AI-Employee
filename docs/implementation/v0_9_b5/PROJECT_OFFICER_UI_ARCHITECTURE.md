# Project Officer UI Architecture

The B5 Windows workspace is a presentation and review layer on top of the B1-B4 planning services.

## Design goals

- keep the Python backend as the source of truth;
- show portfolio, health, change, recommendation, and work-package state in one operator surface;
- preserve read-only preparation boundaries until a human explicitly approves a revision;
- make provenance, freshness, and approval state obvious before any lifecycle transition.

## Structure

- `GaiaShell` owns global app navigation;
- `ProjectOfficerWorkspaceScreen` owns the B5 workspace;
- the controller keeps the current project selection and the selected recommendation/work package context;
- the backend bridge exposes only additive read operations and explicit lifecycle calls.

## Operator behavior

- the operator can inspect health, findings, queue state, and revision history;
- the operator can copy the generated prompt but cannot execute it from the app;
- approval and handoff actions require explicit confirmation and target an exact revision.

