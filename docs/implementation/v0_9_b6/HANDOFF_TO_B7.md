# Handoff to B7

B7 is:

**GAIA v0.9 B7 - Read-Only Dashboard Summary Expansion**

## What B7 may expose

- portfolio health;
- highest-priority recommendations;
- blocked projects;
- pending approvals;
- stale evidence;
- recent completed work;
- trust alerts.

## Dashboard hard boundaries

- no execution controls;
- no approval controls;
- no signing controls;
- no rollback controls;
- no retention controls;
- no direct SQLite or database access.

## Integration rule

The Dashboard should use the official GAIA packages and the integration client through a thin adapter. B7 must not duplicate Project Officer business logic inside the Dashboard.
