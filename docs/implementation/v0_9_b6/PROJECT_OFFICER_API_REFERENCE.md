# Project Officer API Reference

This reference covers the B6 Project Officer API surface only.

## Discovery

### `GET /integration/v1/project-officer/capabilities`

Returns a `ProjectOfficerCapabilityCatalog` payload with:

- `api_version`
- `contract_version`
- `capability_version`
- `capabilities`
- `capability_catalog`
- `degraded_features`

The catalog entries are `CapabilityDescriptor` objects and now include `authority_level`.

## Portfolio and health

### `GET /integration/v1/project-officer/portfolio`

Returns the project-health portfolio.

### `GET /integration/v1/project-officer/projects`

Returns the current Project Officer-visible project list.

### `GET /integration/v1/project-officer/projects/{project_id}/health`

Returns the latest captured project-health snapshot for a project.

### `GET /integration/v1/project-officer/projects/{project_id}/health/snapshots`

Returns the health snapshot history for a project.

Query parameters:

- `limit`
- `offset`

### `GET /integration/v1/project-officer/health-snapshots/{snapshot_id}`

Returns a specific health snapshot by snapshot ID.

## Change intelligence

### `GET /integration/v1/project-officer/changes/portfolio`

Returns the portfolio-level change summary.

### `GET /integration/v1/project-officer/projects/{project_id}/changes/findings`

Returns project-scoped change findings.

Query parameters:

- `severity`
- `direction`
- `change_type`
- `status`
- `limit`
- `offset`

### `GET /integration/v1/project-officer/change-findings/{finding_id}`

Returns a single finding by ID.

### `GET /integration/v1/project-officer/changes/recent`

Returns recent findings, optionally filtered by `project_id`.

## Recommendations

### `GET /integration/v1/project-officer/recommendations/portfolio`

Returns the recommendation portfolio.

### `GET /integration/v1/project-officer/recommendations`

Returns recommendations filtered by:

- `project_id`
- `priority_tier`
- `lifecycle_state`
- `blocked_only`
- `limit`
- `offset`

### `GET /integration/v1/project-officer/recommendations/{recommendation_id}`

Returns a recommendation by ID.

## Work packages

### `GET /integration/v1/project-officer/work-packages`

Returns work packages filtered by:

- `project_id`
- `approval_state`
- `staleness_state`
- `risk_classification`
- `limit`
- `offset`

### `GET /integration/v1/project-officer/projects/{project_id}/work-packages`

Returns the project-scoped work-package list with the same filters as the global list.

### `GET /integration/v1/project-officer/work-packages/{work_package_id}`

Returns a single work package.

### `GET /integration/v1/project-officer/work-packages/{work_package_id}/summary`

Returns the derived summary payload for a work package.

### `GET /integration/v1/project-officer/work-packages/{work_package_id}/prompt`

Returns the rendered prompt payload for a work package.

Query parameters:

- `revision_number`

### `GET /integration/v1/project-officer/work-packages/{work_package_id}/revisions`

Returns the work-package revision history.

### `GET /integration/v1/project-officer/work-package-revisions/{revision_id}`

Returns a single revision by revision ID.

### `GET /integration/v1/project-officer/work-packages/{work_package_id}/approval-decisions`

Returns recorded approval decisions.

### `GET /integration/v1/project-officer/work-packages/{work_package_id}/handoffs`

Returns recorded handoffs.

### `GET /integration/v1/project-officer/work-packages/{work_package_id}/outcomes`

Returns recorded work-package outcomes.

## Lifecycle operations

### `POST /integration/v1/project-officer/work-packages/{work_package_id}/submit-for-review`

Body:

- `revision_number`
- `actor`
- `human_note`

### `POST /integration/v1/project-officer/work-packages/{work_package_id}/approve`

Body:

- `revision_number`
- `actor`
- `human_note`

### `POST /integration/v1/project-officer/work-packages/{work_package_id}/reject`

Body:

- `revision_number`
- `actor`
- `human_note`

### `POST /integration/v1/project-officer/work-packages/{work_package_id}/expire`

Body:

- `reason`

### `POST /integration/v1/project-officer/work-packages/{work_package_id}/handoff`

Body:

- `revision_number`
- `approved_by`
- `next_manual_action`
- `rollback_reference`

### `POST /integration/v1/project-officer/work-packages/{work_package_id}/outcome`

Body:

- `revision_number`
- `outcome`
- `actor`
- `note`

## Response shape

The API returns JSON-ready Pydantic models and plain dicts. The only added contract-specific error envelope is `ProjectOfficerApiError`, which is placed inside `HTTPException.detail`.
