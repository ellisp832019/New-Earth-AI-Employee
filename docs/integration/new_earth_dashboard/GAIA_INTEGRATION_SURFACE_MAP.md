# GAIA Integration Surface Map

## Released Surfaces

| Artifact | Version | Role |
| --- | --- | --- |
| `pyproject.toml` / `src/gaia/__init__.py` | `0.9.0` | GAIA backend release baseline |
| `packages/gaia_integration_client` | `0.9.0` | Official client library |
| `packages/gaia_dashboard_module` | `0.9.0` | Read-only embedded operations workspace |
| `examples/gaia_dashboard_host` | `0.9.0` | Reference host / smoke example |
| `contracts/openapi/gaia-v1.json` | generated | Published OpenAPI contract |

## Package Notes

### `gaia_integration_client`

- Public API is centered on compatibility, capabilities, retention, signing, provenance, trust alerts, and receipt inspection.
- The client is the preferred way to talk to the GAIA backend.

### `gaia_dashboard_module`

- Read-only UI and controller layer for embedded operations.
- Must not expose signing private keys or backend internals.
- Suitable for embedding, not for autonomous execution.

### `gaia_dashboard_conformance`

- No `packages/gaia_dashboard_conformance` package is present in this GAIA repository snapshot.
- Conformance coverage is currently provided by the GAIA test suite and release validation scripts instead.

### `gaia_dashboard_host`

- Reference host used to exercise the module and client together.
- Useful for smoke tests and embedding expectations.

## Backend Capabilities Exposed in the Current Release Line

- compatibility state
- versioned capability catalog
- retention report
- signing key lifecycle
- provenance manifest creation and verification
- trust alerts
- receipt chain inspection

## Host Requirements

- Loopback-only backend URL.
- No direct GAIA SQLite access.
- Signing disabled by default.
- No action execution, rollback, or retention application from the Dashboard module.
- Read-only module embedding only.
