# New Earth Dashboard Integration

GAIA v0.5 exposes a reusable integration contract for dashboard-style clients.

## Contract Goals

- Keep the dashboard read-only unless an explicit action is being created or executed.
- Provide a stable way to query health, compatibility, project summaries, task summaries, approval summaries, action summaries, latest briefs, and receipts.
- Reuse the same contract in the Flutter desktop app and in external dashboard clients.

## Integration Surface

- `GET /integration/v1/status`
- `GET /integration/v1/compatibility`
- `GET /integration/v1/projects`
- `GET /integration/v1/tasks/summary`
- `GET /integration/v1/approvals/summary`
- `GET /integration/v1/actions/summary`
- `GET /integration/v1/briefs/latest`
- `GET /integration/v1/receipts/latest`

## Compatibility Rule

The v0.5 contract reports `contract_version = gaia-v1` and requires a v0.5-compatible backend.

## Reusable Client

The Dart package in `packages/gaia_integration_client` wraps the contract so dashboard code does not have to hand-roll HTTP calls.
