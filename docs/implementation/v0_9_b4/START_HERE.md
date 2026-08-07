# GAIA v0.9 B4 Start Here

GAIA v0.9 B4 turns B3 recommendations into human-reviewable work packages, revision records, approval decisions, and deterministic handoff evidence.

## What shipped

- work-package generation from eligible B3 recommendations;
- stable work-package and revision fingerprints;
- explicit proposed/review/approved/rejected/handoff/outcome states;
- revision history with immutable audit evidence;
- Codex prompt preparation that stops short of execution;
- staleness detection when source evidence changes.

## What stayed out of scope

- automatic Codex invocation;
- automatic execution of work packages;
- writes to external repositories from the B4 service;
- widening the Dashboard trust boundary;
- changing the released `0.8.0` version string.

## Read next

1. [Work Package Architecture](WORK_PACKAGE_ARCHITECTURE.md)
2. [Work Package Schema](WORK_PACKAGE_SCHEMA.md)
3. [Revision Model](REVISION_MODEL.md)
4. [Codex Prompt Generation](CODEX_PROMPT_GENERATION.md)
5. [Prompt Injection Boundary](PROMPT_INJECTION_BOUNDARY.md)
6. [Risk, Backup and Rollback Model](RISK_BACKUP_AND_ROLLBACK_MODEL.md)
7. [Approval State Machine](APPROVAL_STATE_MACHINE.md)
8. [Handoff Model](HANDOFF_MODEL.md)
9. [Security and Authority Proof](SECURITY_AND_AUTHORITY_PROOF.md)
10. [Validation Evidence](VALIDATION_EVIDENCE.md)
11. [Handoff to B5](HANDOFF_TO_B5.md)
