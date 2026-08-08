# Change Proposal Model

## Canonical Inputs

The C3 proposal model is intentionally small and typed.

Required semantic fields:

- `proposal_id`
- `revision`
- `title`
- `origin_project`
- `objective`
- `change_type`
- `target_entities`

Supporting fields:

- `proposed_contract_changes`
- `affected_versions`
- `evidence`
- `blocked_by`
- `depends_on`
- `required_validation`
- `rollback_concept`
- `recommended_order`
- `status`
- `human_decision`

## Change Types

Supported change types are a closed canonical set:

- `API_CHANGE`
- `PACKAGE_UPGRADE`
- `SCHEMA_CHANGE`
- `FIRMWARE_PROTOCOL_CHANGE`
- `REPOSITORY_RESTRUCTURE`
- `RELEASE_VERSION_CHANGE`
- `HARDWARE_INTERFACE_CHANGE`
- `SHARED_LIBRARY_CHANGE`
- `PROJECT_CONTRACT_CHANGE`

## Identity and Revision

- Proposal identity is computed from semantic content.
- Proposal revision identity is computed from the revision-specific canonical payload.
- Equivalent canonical proposals produce the same semantic fingerprint.
- Revision changes produce a new revision fingerprint.

## Fail-Closed Targeting

Targets must map to canonical IDs where possible.

Unknown targets are not treated as safe or ignored.
