# Handoff to C5

## What C5 May Consume

C5 may consume the following canonical C4 outputs:

- `ProgrammeRoadmapPortfolio`
- `ProgrammeRoadmapItem`
- `ReleaseTrainPortfolio`
- `ReleaseTrainRecord`
- `ReleaseTrainParticipant`
- `ReleaseTrainVersionRequirement`
- roadmap fingerprints
- release-train fingerprints
- compatibility constraints
- rollback relationships
- validation references
- release-readiness and human-approval states

## Known Limitations

- no human-reviewable programme package builder was added in C4;
- no UI or public API surface was added;
- no programme-package persistence layer was added;
- no release automation was added;
- no schema bump was added.

## Next Branch

Recommended next branch:

- `planning/gaia-v0.10-c5-programme-packages`

## C5 Boundary

C5 may use C4 as an input source, but it must not reimplement roadmap scoring or release-train discovery.
