# Public Programme API

## Purpose

Expose the canonical GAIA programme intelligence as public, read-only, versioned routes.

## Added Routes

- `/integration/v1/programme/summary`
- `/integration/v1/programme/overview`
- `/integration/v1/architecture/entities`
- `/integration/v1/architecture/entities/{entity_id}`
- `/integration/v1/architecture/relationships`
- `/integration/v1/architecture/relationships/{relationship_id}`
- `/integration/v1/dependencies/graph`
- `/integration/v1/dependencies/findings`
- `/integration/v1/dependencies/cycles`
- `/integration/v1/dependencies/shared`
- `/integration/v1/dependencies/orphans`
- `/integration/v1/dependencies/projects/{project_id}`
- `/integration/v1/dependencies/projects/{project_id}/dependents`
- `/integration/v1/change-impact/summary`
- `/integration/v1/change-impact/recommendations`
- `/integration/v1/change-impact/recommendations/{recommendation_id}`
- `/integration/v1/programme/roadmap`
- `/integration/v1/release-trains`
- `/integration/v1/programme-packages`
- `/integration/v1/programme-packages/{package_id}`

## Boundary

The C6 internal `/integration/v1/project-officer/programme/workspace` endpoint remains internal and excluded from the public contract.
