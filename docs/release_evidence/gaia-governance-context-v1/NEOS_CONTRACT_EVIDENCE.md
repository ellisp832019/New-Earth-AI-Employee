# NEOS Contract Evidence

## Client

`src/gaia/governance_context.py` contains the `NeosGovernanceClient`.

## Contract Properties

- read-only HTTP client;
- configurable base URL;
- local-first default `http://127.0.0.1:8765`;
- bounded timeout;
- JSON validation;
- schema/version compatibility handling;
- degraded/unavailable fallback models;
- no NEOS Python imports;
- no NEOS database access;
- no write endpoints.

## Observed Endpoints

- `/governance`
- `/governance/status`
- `/governance/findings`
- `/governance/project/{project_id}`
- `/governance/snapshot`

## Preservation

Source snapshots, findings, and cache records preserve source metadata where available.
