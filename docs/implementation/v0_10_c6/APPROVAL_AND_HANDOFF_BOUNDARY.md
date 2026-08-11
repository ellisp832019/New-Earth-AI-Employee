# Approval and Handoff Boundary

## Approval

C6 does not add a new approval executor.

Where approval records are displayed, the UI:

- shows the exact revision and fingerprint;
- makes the human decision explicit;
- does not execute work;
- does not mutate external repositories;
- does not invoke Codex.

## Handoff

The workspace may display handoff evidence if present in the backend payload.

It does not:

- run Codex;
- launch prompt execution;
- create branches;
- commit;
- push;
- merge;
- publish releases.
