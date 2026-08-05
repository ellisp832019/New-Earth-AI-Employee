# Architecture

GAIA is a local-first AI employee foundation built around strict evidence, safety, and approval boundaries.

## Layers

- Python backend for project inspection, workflows, approvals, and output execution.
- FastAPI service for structured local API access.
- Typer CLI for operator workflows.
- Flutter Windows desktop client for visual control.
- Shared Dart integration client for dashboard-style consumption.

## v0.5 Output Workspace

- Permission manifests define what an action may do.
- Actions hold the exact proposed write.
- Approvals bind a reviewer decision to a specific action and manifest version.
- Execution receipts capture the final result.
- Backup and rollback records preserve recovery paths.

## Security Shape

- Default deny for writes.
- Canonical path checks against a GAIA-owned workspace.
- No automatic Git commit or push behavior.
- Explicit user confirmation before execution.

## External Contract

The stable integration surface is `gaia-v1`, exported via OpenAPI and mirrored in the reusable Dart client.
