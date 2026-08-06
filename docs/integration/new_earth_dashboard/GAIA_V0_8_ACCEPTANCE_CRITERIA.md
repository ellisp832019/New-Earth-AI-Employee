# GAIA v0.8 Acceptance Criteria

- Dashboard uses the official GAIA packages rather than recreated backend logic.
- Dashboard never reads GAIA SQLite directly.
- Dashboard never accesses GAIA runtime files directly.
- Dashboard never accesses MicroGrow directly for this integration.
- Incompatible backend state fails safely and does not crash the app.
- Unavailable backend state preserves stale data and labels it clearly.
- Capability gates hide or disable features the backend does not report.
- The embedded module remains read-only.
- The embedded module cannot execute actions.
- The embedded module cannot manage signing keys.
- The embedded module cannot apply retention.
- Trust warnings and provenance warnings are visible.
- The standalone GAIA Control Centre remains available.
- Existing Dashboard features remain unaffected.
- Windows build passes.
- Current Dashboard tests remain green.
- GAIA conformance and release validation pass.
