# Security and Authority Proof

B5 keeps the approval boundary narrow.

## Proof points

- the Python backend remains the source of truth;
- the Windows app talks to the backend through the managed API only;
- no SQLite reads occur in Flutter;
- no autonomous execution path is exposed;
- no external repository writes are performed by the workspace;
- MicroGrow and the Dashboard are read-only evidence sources for this phase.

## Lifecycle authority

- approval and handoff are exact-revision transitions;
- stale and expired packages stay blocked;
- the prompt can be copied only for manual use.

