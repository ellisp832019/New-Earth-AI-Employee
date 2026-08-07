# Handoff Model

Handoff is the explicit bridge between human approval and downstream execution.

## Required inputs

- approved revision number;
- approval decision record;
- prompt fingerprint;
- source evidence identifiers and fingerprints;
- rollback reference.

## Behavior

- a handoff can only occur after approval;
- the handoff record binds the exact approved revision;
- the handoff record does not itself execute the work;
- outcomes are recorded later as completed, failed, or rolled back.
