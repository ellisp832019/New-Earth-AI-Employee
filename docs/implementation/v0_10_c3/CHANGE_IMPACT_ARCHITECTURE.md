# Change Impact Architecture

## Service Shape

`ChangeImpactService` is a pure analysis service.

It consumes:

- `ChangeProposal`;
- `ProjectContractService`;
- `ArchitectureRegistryService`;
- `DependencyGraphService`;
- the local database for read-only work-package inspection.

It produces a typed `ChangeImpactResult`.

## Analysis Flow

1. Normalize the proposal into a deterministic canonical form.
2. Resolve proposal targets against canonical project, entity, contract, and work-package records.
3. Build the canonical dependency graph.
4. Traverse direct and transitive dependents from the resolved targets.
5. Project entity impacts into project impacts.
6. Resolve affected contracts, releases, work packages, validation references, refresh requirements, sequencing constraints, and unknown findings.
7. Calculate a deterministic structural risk result.
8. Fingerprint the full result from canonical semantic inputs only.

## Determinism Rules

- Proposal identity is separated from proposal revision identity.
- Fingerprints ignore timestamps and generated provenance capture times.
- Ordering is canonicalized before hashing or return.
- Unknown targets and missing canonical records fail closed.

## No Duplicate Graph

The service does not persist or rebuild a second graph. It relies on the C2 graph as the canonical traversal source.
