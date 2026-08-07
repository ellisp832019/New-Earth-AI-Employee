# Work Package Architecture

The B4 service lives in `src/gaia/work_packages.py` and is wired into `ProjectService` as a dedicated layer above B3 recommendations.

## Responsibilities

- accept only eligible recommendations;
- derive a deterministic work-package scope from B1, B2, and B3 evidence;
- persist a package record plus an append-only revision record;
- prepare a human-reviewable Codex prompt;
- track approval, handoff, outcome, and staleness state.

## Design rules

- a package is created for review, not execution;
- the package identity is stable for a semantic recommendation payload;
- the current revision is always the only revision eligible for approval;
- stale packages are detected from recommendation, project-config, and health-snapshot drift;
- external repos remain read-only from this service.

## Code references

- `src/gaia/work_packages.py`
- `src/gaia/service.py`
- `src/gaia/db.py`
- `src/gaia/models.py`
