# Data Model

GAIA v0.5 extends the SQLite schema with permissioned output workspace records.

## New Tables

- `permission_manifests`
- `output_actions`
- `action_previews`
- `execution_receipts`
- `output_backups`
- `rollback_records`

## Updated Records

- `approvals` now stores action-binding columns so a review decision cannot drift away from the action it approved.

## Model Relationships

- One permission manifest can authorize many actions.
- One action can create many previews but only one execution receipt.
- One receipt can point to one backup and one rollback record.
- One approval is bound to one action and one manifest version.

## Storage Rules

- JSON fields are stored as serialized text in SQLite.
- Content hashes are SHA-256 values.
- Workspace-relative paths are stored in display-friendly form after canonical safety checks.
