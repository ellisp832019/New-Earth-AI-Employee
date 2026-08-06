# GAIA v0.8.0 Release Notes

GAIA v0.8.0 closes out the cross-repository acceptance work for the New Earth Dashboard integration and records the final release evidence after Dashboard PR #3 and PR #4 were merged.

## Highlights

- Phase A established the Dashboard integration audit and approved the thin-adapter architecture.
- Phase B delivered the read-only Dashboard surface under `/more/ai-employee`.
- The Dashboard now consumes the official `gaia_integration_client` and `gaia_dashboard_module` packages.
- The Dashboard feature flag is disabled by default and gates the GAIA surface in Settings.
- Compatibility and capability discovery are surfaced without exposing backend write authority.
- Unavailable backend state fails closed and preserves stale data.
- Trust and provenance information is presented as read-only summaries.
- The standalone GAIA Control Centre remains the authority for execution, rollback, retention application, and signing-key management.

## Cross-Repository Acceptance

- Dashboard PR #3 merged the GAIA v0.8 read-only integration.
- Dashboard PR #4 merged the Windows startup and analyzer repair.
- Final accepted Dashboard main SHA: `aeb8dcc38b52316aa53660b9af9523cc1b41eddf`.

## Versioning and Contract Notes

- Backend product version and package versions are now aligned to `0.8.0`.
- The compatibility contract remains backward-aware for the released Dashboard integration.
- OpenAPI contract regeneration is deterministic and remains repository-managed.

## Validation Summary

- GAIA backend validation passed.
- Official package validation passed for the integration client, dashboard module, and host example.
- Dashboard acceptance evidence remains valid.
- MicroGrow stayed read-only and unchanged.

## Safety

- The embedded GAIA surface remains read-only.
- No direct GAIA SQLite access was introduced in the Dashboard.
- No MicroGrow code or state was modified during the closeout.
