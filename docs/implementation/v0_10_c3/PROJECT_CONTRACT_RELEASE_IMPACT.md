# Project Contract and Release Impact

## Canonical Contract Handling

Only existing canonical contract records are treated as authoritative.

If the proposal targets a project contract, the service may project a preview contract by applying the proposed changes in memory, but it does not persist that preview.

## Release Impact

Release impacts are emitted only when a canonical project contract provides release metadata such as:

- version;
- release process reference;
- version constraint.

If release metadata is missing, the result reports the gap as unknown or unverified.

## No Release Train Logic

This phase does not create roadmap states or release trains.

It only reports the deterministic structural consequences of the change against the current canonical release metadata.
