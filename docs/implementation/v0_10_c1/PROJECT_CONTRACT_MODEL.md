# Project Contract Model

The project contract is the canonical, deterministic description of a configured GAIA project.

## Core Fields

- `project_id`
- `name`
- `repository`
- `status`
- `authority_level`
- `version`
- `release_channel`
- `documentation_roots`
- `security_boundary`
- `evidence_freshness_policy`

## Behaviour

- the contract is bootstrapped from `config/projects.yaml`;
- the bootstrap revision is approved and reproducible;
- identical content hashes to the same semantic revision;
- revision history is retained locally in SQLite;
- approved state is preserved independently from newly created draft revisions.

## Boundary

- The contract only describes the local, configured GAIA project universe.
- It does not authorise writes to external repositories.
- It does not replace the existing v0.9 project-health or recommendation models.
