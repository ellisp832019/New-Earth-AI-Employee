# GAIA v0.6.0 Release Notes

GAIA v0.6.0 introduces the dashboard integration and trust layer.

## Highlights

- Reusable Flutter `gaia_dashboard_module` package.
- Self-contained example dashboard host in this repository.
- Stronger compatibility contract with degraded-mode reporting.
- Tamper-evident receipt chains and receipt verification commands.
- Deterministic offline review package creation and verification.
- Versioned action templates and retention policy scaffolding.
- Trust Centre and integration screens in the Windows control centre.

## Safety

- The embedded dashboard surface remains read-mostly.
- Action execution still stays in the dedicated GAIA Windows Control Centre or CLI path.
- MicroGrow and the separate New Earth Dashboard repository are not modified by this milestone.
