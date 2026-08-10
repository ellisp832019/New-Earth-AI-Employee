# Handoff to C6

## What C6 May Consume

C6 may consume the following canonical C5 outputs:

- `ProgrammePackagePortfolio`
- `ProgrammePackageRecord`
- `ProgrammePackageRevisionRecord`
- `ProgrammePackageWorkPackageReference`
- `ProgrammePackageRiskRecord`
- `ProgrammePackageProjectAcceptanceRecord`
- `ProgrammePackageHumanApprovalRecord`
- package fingerprints
- package revision history
- rollback coordination
- acceptance criteria

## Known Limitations

- no Windows workspace UI was added in C5;
- no package execution engine was added;
- no API or CLI exposure was added;
- no Dashboard mutation was added;
- no MicroGrow mutation was added.

## Next Branch

Recommended next branch:

- `planning/gaia-v0.10-c6-windows-programme-workspace`

## C6 Boundary

C6 may display and review C5 packages, but it must not execute them or bypass the human approval rule.
