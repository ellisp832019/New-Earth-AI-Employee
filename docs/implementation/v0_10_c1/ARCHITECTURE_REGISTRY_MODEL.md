# Architecture Registry Model

The architecture registry stores deterministic identity records for projects, packages, services, and their relationships.

## Entity Model

- entities have a stable `identity_key`;
- supported kinds include `project`, `service`, `package`, `library`, `api`, `database`, `firmware`, `hardware`, and `relationship-aware` supporting types;
- provenance is captured on every revision;
- current records point at the latest stored revision.

## Relationship Model

- relationships are explicit and directional;
- relationship revisions are deterministic and history-preserving;
- the registry rejects references to unknown entities;
- self-referential relationships are rejected.

## Boundary

- the registry is read-only with respect to external repositories;
- it is a local control-plane data model, not a deployment system;
- it intentionally stops before dependency traversal and impact scoring.
