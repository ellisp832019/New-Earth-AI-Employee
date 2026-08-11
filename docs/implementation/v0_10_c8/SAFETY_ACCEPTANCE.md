# Safety Acceptance

## Not Introduced in v0.10

- arbitrary command execution;
- autonomous shell execution;
- autonomous Codex execution;
- autonomous Git operations;
- automatic branch creation;
- automatic commits;
- automatic pushes;
- automatic PR merges;
- autonomous release publication;
- external repository writes;
- Dashboard approval actions;
- Dashboard package mutation;
- direct Dashboard SQLite access;
- MicroGrow write or control expansion;
- cloud fallback;
- mandatory telemetry;
- automatic model downloads;
- hardware-control expansion.

## Fail-Closed Rule

If authority, provenance, or freshness is ambiguous, the system must report partial, stale, conflicting, or unavailable rather than silently treating the state as safe.

## Human Approval

Programme packages and work packages remain planning and review artifacts. Human approval remains mandatory and must not self-execute.
