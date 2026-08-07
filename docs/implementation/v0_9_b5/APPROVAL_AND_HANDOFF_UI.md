# Approval and Handoff UI

Approval and handoff are explicit backend-authorised transitions.

## Approval review

- show work-package ID;
- show revision number and project;
- show risk, freshness, fingerprint, and staleness;
- require confirmation before the lifecycle call is made.

## Handoff review

- show the approved revision;
- show the prompt fingerprint and rollback reference;
- require an explicit confirmation before the handoff record is created;
- display the next manual action after recording the handoff.

## Authority rule

The app requests transitions from the backend state machine. It does not decide independently whether a state transition is valid.

