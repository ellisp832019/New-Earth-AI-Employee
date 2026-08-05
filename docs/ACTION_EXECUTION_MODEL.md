# Action Execution Model

Output actions are explicit records of a requested write into the GAIA-owned workspace.

## Supported Actions

- `create_output_file`
- `update_output_file`
- `export_draft`
- `export_report`
- `export_daily_brief`
- `create_generated_document`
- `rollback_output_file`

## Execution Flow

1. Create an action against a permission manifest.
1. Generate an exact preview and content hash.
1. Request approval.
1. Approve the action.
1. Execute only after an explicit user confirmation token.
1. Record a receipt and any backup created before the write.

## Execution Guarantees

- The target file path must remain inside the allowed root.
- The resulting content hash must match the proposed hash.
- Approval binding must still match the action at execution time.
- A changed target or changed manifest invalidates the action.

## Live Proof

The v0.5 workflow executed `create_output_file` action `5ed1721f-c512-47fb-b0f9-f620a19256cc` and `update_output_file` action `fff38afe-83d0-4045-b6ee-54cab244b4e6`, producing receipts and a rollback record.
