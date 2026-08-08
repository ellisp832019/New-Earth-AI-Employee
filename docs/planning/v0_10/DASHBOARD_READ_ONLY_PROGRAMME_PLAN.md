# Dashboard Read-Only Programme Plan

## Objective

The New Earth Dashboard may eventually show programme summaries, but it must remain read only and must not touch GAIA SQLite directly.

## Candidate Read-Only Views

- portfolio health;
- architecture health;
- cross-project blockers;
- top programme recommendations;
- release trains;
- major change impacts;
- pending programme approvals;
- stale cross-project evidence;
- trust alerts.

## Prohibited Actions

- approve;
- reject;
- hand off;
- execute;
- alter programme packages;
- modify projects;
- run Codex;
- access GAIA SQLite directly.

## Boundary Rule

If the backend is unavailable or incompatible, the Dashboard must fail closed and show the state explicitly.
