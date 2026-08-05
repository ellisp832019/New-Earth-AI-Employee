# Security Model

GAIA v0.5 is designed to make accidental writes, hidden writes, and ambiguous execution hard to do.

## Controls

- Allowlisted output roots only.
- Permission manifests for output actions.
- Explicit approval requests and approval bindings.
- Explicit confirmation tokens for execution and rollback.
- Execution receipts and backups for post-action review.

## Path Safety

- Traversal is rejected.
- Hidden `.git` paths are rejected.
- Reserved Windows names are rejected.
- UNC, device, and ADS-style paths are rejected.
- Targets must remain inside the configured GAIA-owned workspace.

## Operational Boundaries

- MicroGrow remains read-only.
- The backend never commits or pushes Git changes automatically.
- The desktop client surfaces the safety posture instead of bypassing it.

## Evidence

Every write produces a receipt. Overwrite-style writes can also produce a backup and a later rollback record.
