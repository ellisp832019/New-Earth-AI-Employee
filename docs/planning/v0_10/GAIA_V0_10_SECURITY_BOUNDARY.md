# GAIA v0.10 Security Boundary

## Authority Boundary

GAIA may:

- read approved project and repository evidence;
- derive deterministic programme intelligence;
- prepare human-reviewable programme packages;
- expose read-only client and Dashboard views;
- record provenance for decisions and evidence.

GAIA must not:

- run Codex automatically;
- execute arbitrary commands;
- modify external repositories;
- create or merge external branches;
- push external changes;
- approve its own work;
- control hardware;
- send external messages;
- download models automatically;
- fall back to cloud systems without explicit human choice.

## Read-Only Surfaces

- The New Earth Dashboard must remain read only.
- The Dashboard must never access GAIA SQLite directly.
- The Windows app is the trusted operator workspace, not an execution engine.

## Fail-Closed Rule

If authority, provenance, or freshness is ambiguous, the system must report partial, stale, conflicting, or unavailable rather than silently treating the state as safe.
