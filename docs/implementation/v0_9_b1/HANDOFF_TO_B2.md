# Handoff to B2

B1 is the registry-and-health foundation. B2 should build on this without changing the isolation model.

## Recommended next steps

- add change intelligence over the recorded health snapshots;
- compare project health over time;
- introduce prioritisation rules;
- keep the public project API stable;
- continue treating Dashboard and MicroGrow as read-only evidence sources.

## What not to do

- do not expand write access;
- do not weaken the canonical-root checks;
- do not add automation that mutates external repositories;
- do not rework the B1 snapshot format unless a schema migration is planned with it.
