# Project Contract Model

## Purpose

The Project Contract is the canonical engineering identity for an approved project. It captures what the project is, what it depends on, what it exposes, and what evidence is needed to trust it.

## Minimum Canonical Fields

- `project_id`
- `name`
- `repository`
- `project_type`
- `owner`
- `purpose`
- `status`
- `authority_level`
- `primary_technologies`
- `supported_platforms`
- `interfaces_exposed`
- `interfaces_consumed`
- `dependencies`
- `shared_packages`
- `hardware_dependencies`
- `data_contracts`
- `api_contracts`
- `release_channel`
- `version`
- `criticality`
- `risk_class`
- `documentation_roots`
- `test_commands`
- `build_commands`
- `release_process_reference`
- `architecture_references`
- `known_constraints`
- `security_boundary`
- `evidence_freshness_policy`

## Model Rules

- Not every field must be mandatory.
- Stable identity matters more than verbose metadata.
- Derived relationship data belongs in the dependency graph, not duplicated as canonical truth in every contract.
- Contract revisions must be immutable once approved.
