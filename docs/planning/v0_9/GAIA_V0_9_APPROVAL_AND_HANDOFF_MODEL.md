# GAIA v0.9 Approval and Handoff Model

## States

- proposed;
- under_review;
- approved;
- rejected;
- superseded;
- expired;
- handed_off;
- completed;
- failed;
- rolled_back.

## Approval Rules

- No approval state should execute work automatically.
- Approval must be explicit and auditable.
- Approved packages must still require the correct execution boundary.
- Expiry should invalidate stale plans rather than silently allowing them.

## Handoff Rule

Handoffs should capture:

- who approved the package;
- what exactly was approved;
- what evidence was used;
- what the next manual action is;
- what rollback or recovery path exists.
