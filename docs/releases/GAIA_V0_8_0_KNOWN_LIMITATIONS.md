# GAIA v0.8.0 Known Limitations

- The Dashboard embedded GAIA surface is intentionally read-only.
- Execution, rollback, retention application, and signing-key management remain in the standalone GAIA Control Centre.
- The compatibility contract remains backward-aware and does not claim a semantic API overhaul.
- The broader Dashboard widget suite still has unrelated stale expectation drift, which is not GAIA-specific.
- No standalone `packages/gaia_dashboard_conformance` package exists in this repository snapshot.
- Validation relies on repository scripts plus the official GAIA package tests and host example.
- MicroGrow remains out of scope and must stay read-only.
- The release branch is not tagged or published yet.
