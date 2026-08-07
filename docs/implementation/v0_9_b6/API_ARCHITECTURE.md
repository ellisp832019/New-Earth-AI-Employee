# API Architecture

B6 keeps the backend as the single source of truth and exposes the Project Officer surface as a thin compatibility layer.

## Structure

- `src/gaia/project_officer.py` wraps the existing `ProjectService` and `Database` helpers.
- `src/gaia/api.py` mounts versioned `/integration/v1/project-officer/*` routes on top of that wrapper.
- `src/gaia/models.py` now carries the shared `authority_level` field on `CapabilityDescriptor`.
- `contracts/openapi/gaia-v1.json` was regenerated from the live application schema after the B6 routes were added.

## Route groups

### Discovery

- `GET /integration/v1/project-officer/capabilities`

### Portfolio and health

- `GET /integration/v1/project-officer/portfolio`
- `GET /integration/v1/project-officer/projects`
- `GET /integration/v1/project-officer/projects/{project_id}/health`
- `GET /integration/v1/project-officer/projects/{project_id}/health/snapshots`
- `GET /integration/v1/project-officer/health-snapshots/{snapshot_id}`

### Change intelligence

- `GET /integration/v1/project-officer/changes/portfolio`
- `GET /integration/v1/project-officer/projects/{project_id}/changes/findings`
- `GET /integration/v1/project-officer/change-findings/{finding_id}`
- `GET /integration/v1/project-officer/changes/recent`

### Recommendations

- `GET /integration/v1/project-officer/recommendations/portfolio`
- `GET /integration/v1/project-officer/recommendations`
- `GET /integration/v1/project-officer/recommendations/{recommendation_id}`

### Work packages

- `GET /integration/v1/project-officer/work-packages`
- `GET /integration/v1/project-officer/projects/{project_id}/work-packages`
- `GET /integration/v1/project-officer/work-packages/{work_package_id}`
- `GET /integration/v1/project-officer/work-packages/{work_package_id}/summary`
- `GET /integration/v1/project-officer/work-packages/{work_package_id}/prompt`
- `GET /integration/v1/project-officer/work-packages/{work_package_id}/revisions`
- `GET /integration/v1/project-officer/work-package-revisions/{revision_id}`
- `GET /integration/v1/project-officer/work-packages/{work_package_id}/approval-decisions`
- `GET /integration/v1/project-officer/work-packages/{work_package_id}/handoffs`
- `GET /integration/v1/project-officer/work-packages/{work_package_id}/outcomes`

### Lifecycle

- `POST /integration/v1/project-officer/work-packages/{work_package_id}/submit-for-review`
- `POST /integration/v1/project-officer/work-packages/{work_package_id}/approve`
- `POST /integration/v1/project-officer/work-packages/{work_package_id}/reject`
- `POST /integration/v1/project-officer/work-packages/{work_package_id}/expire`
- `POST /integration/v1/project-officer/work-packages/{work_package_id}/handoff`
- `POST /integration/v1/project-officer/work-packages/{work_package_id}/outcome`

## Implementation note

The API routes do not embed new business logic. They delegate to the existing project-health, change, recommendation, and work-package services, and translate errors into a structured B6 envelope.
