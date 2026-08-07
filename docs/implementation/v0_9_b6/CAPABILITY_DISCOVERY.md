# Capability Discovery

B6 adds a dedicated Project Officer capability catalog without replacing the older integration compatibility endpoint.

## Existing compatibility surface

- `/integration/v1/compatibility` still comes from `GAIATrustService`.
- That compatibility payload continues to expose the older integration contract and capability payload for v0.8-compatible consumers.

## New B6 discovery surface

- `/integration/v1/project-officer/capabilities` returns a `ProjectOfficerCapabilityCatalog`.
- The catalog uses:
  - `api_version = 0.9.0`
  - `contract_version = gaia-v3`
  - `capability_version = 0.9.0`

## Capability descriptors

Each `CapabilityDescriptor` includes:

- `capability_id`
- `version`
- `state`
- `summary`
- `authority_level`
- `gated_by`
- `requires_signing`
- `enabled`

## Actual capability groups

- `project_officer_portfolio`
- `project_officer_project_health`
- `project_officer_change_intelligence`
- `project_officer_recommendations`
- `project_officer_work_packages`
- `project_officer_lifecycle_review`
- `project_officer_lifecycle_approval`
- `project_officer_lifecycle_handoff`
- `project_officer_lifecycle_outcome`
- `windows_project_officer_workspace`
- `dashboard_read_only_compatibility`

## Authority levels used

- `read_only`
- `gaia_local_state`
- `manual_handoff_only`

These authority labels are descriptive only. They do not grant execution capability.
