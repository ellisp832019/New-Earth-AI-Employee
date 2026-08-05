# GAIA v0.4 Live Workflow

## Read-Only MicroGrow Flow

The following local read-only flow was executed against `microgrow-v1`:

1. `gaia project scan microgrow-v1`
2. `gaia project snapshot microgrow-v1`
3. `gaia ask microgrow-v1 "What should I build next?" --deterministic-only`
4. `gaia ask microgrow-v1 "Create the next Codex prompt" --deterministic-only`
5. `gaia tasks from-run <run-id>`
6. `gaia drafts create`
7. `gaia approvals create`
8. `gaia approvals approve`
9. `gaia drafts revise`
10. `gaia briefs daily`

## Recorded IDs

- Snapshot ID: `e4662ada-a2b7-4913-b8f0-8cf9e50b555f`
- Ask run ID: `e5048b03-770a-4d56-8222-2369f9323917`
- Prompt-draft run ID: `9d76abe2-b60f-45c1-8b6b-ae542564cebd`
- Task ID: `7b2e68bd-0170-45fe-8060-b9b9f54725c2`
- Draft ID: `91133bd7-7229-412d-ae33-83e21bb4f05d`
- Approval ID: `6cce7956-68c3-4bf1-ad1a-4a12e109f69b`
- Brief ID: `b61eb0b8-0d6f-4742-a7f6-2c8895d645fd`

## Outcome

- The task was created in `proposed` status.
- The draft content was labeled `DRAFT - NOT EXECUTED`.
- The approval was created, approved for manual use, and then invalidated after the draft changed.
- The daily brief was generated deterministically.
- MicroGrow branch, SHA, and porcelain status remained unchanged.
