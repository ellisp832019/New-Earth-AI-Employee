# Handoff to C4

## What C4 May Consume

C4 may consume the following canonical C3 outputs:

- `ChangeProposal`
- `ChangeImpactService`
- `ChangeImpactResult`
- proposal identity and revision fingerprints
- impact fingerprint
- direct affected entities
- transitive affected entities
- affected projects
- affected contracts
- affected releases
- affected work packages
- validation references
- refresh requirements
- sequencing constraints
- structural risk and reason codes
- unknown findings
- freshness and trust aggregation

## Known Limitations

- no persistent change-proposal table was added in C3;
- no programme roadmap logic was added;
- no release trains were added;
- no programme packages were added;
- no UI or public API surface was added.

## Next Branch

Recommended next branch:

- `planning/gaia-v0.10-c4-programme-roadmap-release-trains`

## C4 Boundary

C4 may use C3 as an input source, but it must not reimplement change-impact analysis or assume that unknown findings are safe.
