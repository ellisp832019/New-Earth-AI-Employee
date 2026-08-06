# Recommended GAIA Dashboard Architecture

## Target Shape

| Element | Owner | Recommendation |
| --- | --- | --- |
| Route location | Dashboard repo | `/more/ai-employee` |
| Module entry point | Dashboard repo | A new dashboard-owned adapter screen or shell wrapper |
| GAIA client dependency | Dashboard repo | Pinned dependency on `gaia_integration_client` |
| GAIA embedded module dependency | Dashboard repo | Pinned dependency on `gaia_dashboard_module` |
| Backend URL configuration | Dashboard repo | Loopback-only configuration with explicit local host/port |
| Compatibility gate | Dashboard repo | Adapter checks before rendering the module |
| Capability gate | Dashboard repo + GAIA | Dashboard renders only capabilities the backend reports |
| Cache policy | Dashboard repo | Cache last successful snapshots locally, label stale data clearly |
| Stale-data UX | Dashboard repo | Show a stale banner and preserve the last known good state |
| Trust Centre entry point | Dashboard repo | Link from the GAIA surface into dashboard trust and security views |
| Deep links to standalone Control Centre | Dashboard repo | Explicit link-out action only |
| Diagnostics flow | Dashboard repo | Connection health, capability view, then trust/provenance details |
| Conformance tests | Both repos | GAIA tests plus Dashboard smoke and route tests |
| Feature flag | Dashboard repo | Disabled by default until the route and adapter are ready |
| Rollback strategy | Dashboard repo | Keep route hidden and feature-flagged so it can be removed without touching GAIA packages |

## Ownership Split

### GAIA repository owns

- `packages/gaia_integration_client`
- `packages/gaia_dashboard_module`
- `contracts/openapi/gaia-v1.json`
- backend compatibility, capabilities, provenance, trust, retention, and signing APIs
- standalone GAIA control centre behavior

### Dashboard repository owns

- route entry and shell placement
- feature flag and release toggle
- adapter controller and view composition
- stale-data and degraded-state UX
- dashboard-side diagnostics and tests

## Important Constraint

The Dashboard should depend on GAIA packages, not recreate GAIA backend state or signing logic.
