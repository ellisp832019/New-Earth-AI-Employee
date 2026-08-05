# Execution Receipts

Execution receipts are the durable record that a write actually happened.

## What a Receipt Stores

- Receipt ID
- Action ID
- Approval ID
- Manifest ID and version
- Target path
- Previous hash
- Resulting hash
- Operator
- Timestamp
- Backup path, if any
- Rollback availability
- Warnings and result metadata

## Why Receipts Matter

- They prove execution was explicit.
- They support audit review.
- They provide the rollback link back to the protected backup.
- They allow dashboard integrations to show completed work without guessing.

## Live Proof

The accepted v0.5 create action produced receipt `5430a05b-8855-4dba-949e-3c34713a7848`.
The update action produced receipt `6a7dc8e6-933d-4e79-a1f0-6862cb24ae97`.
