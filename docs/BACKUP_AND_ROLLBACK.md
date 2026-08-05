# Backup and Rollback

GAIA v0.5 creates backups before overwrite-style output writes when the manifest requires it.

## Backup Behavior

- Backups are stored under `workspace/backups`.
- Backup files preserve the pre-write content.
- A backup record captures the backup hash and target path.

## Rollback Behavior

- Rollback is only available when a receipt indicates that it is allowed.
- Rollback restores the backup content back to the target file.
- Rollback produces its own record and marks the action as rolled back.

## Safety Notes

- Backup and rollback paths are still subject to path-safety checks.
- A rollback is not a silent undo; it is a new controlled action with its own evidence.

## Live Proof

The update action `fff38afe-83d0-4045-b6ee-54cab244b4e6` created backup `workspace/backups/fff38afe-83d0-4045-b6ee-54cab244b4e6/live-demo.md.20260805131247.bak`.
Rollback record `62983321-5310-454b-b537-3e6994a63a09` restored the prior content successfully.
