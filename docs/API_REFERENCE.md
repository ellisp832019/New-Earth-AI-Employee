# API Reference

This repository exposes a local GAIA API through FastAPI.

## Core Endpoints

- `GET /health`
- `GET /projects`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/scan`
- `GET /tasks`
- `POST /tasks`
- `GET /drafts`
- `POST /drafts`
- `GET /approvals`
- `POST /approvals`
- `GET /briefs`

## v0.5 Output Workspace Endpoints

- `GET /permissions`
- `POST /permissions`
- `GET /permissions/{manifest_id}`
- `POST /permissions/{manifest_id}/validate`
- `POST /permissions/{manifest_id}/review`
- `GET /actions`
- `POST /actions`
- `GET /actions/{action_id}`
- `POST /actions/{action_id}/preview`
- `POST /actions/{action_id}/request-approval`
- `POST /actions/{action_id}/approve`
- `POST /actions/{action_id}/execute`
- `POST /actions/{action_id}/rollback`
- `POST /actions/{action_id}/cancel`
- `GET /receipts`
- `GET /receipts/{receipt_id}`

## Integration Endpoints

- `GET /integration/v1/status`
- `GET /integration/v1/compatibility`
- `GET /integration/v1/actions/summary`
- `GET /integration/v1/receipts/latest`

## Design Notes

- Output writes are only allowed through explicit permission manifests.
- Execution requires an approval binding and an explicit confirmation token.
- Receipts and backups are first-class API objects.
