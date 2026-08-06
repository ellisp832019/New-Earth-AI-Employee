# GAIA v0.6 Known Limitations

- The dashboard module is intentionally read-mostly.
- Action execution remains in the Windows Control Centre and CLI only.
- Review-package verification is offline and hash-based rather than key-signed.
- Retention is default-preserve and still requires explicit approval for any cleanup.
- The separate New Earth Dashboard repository is not modified in this milestone.
- The first CI pass exposed a clean-runner Python-resolution defect in `scripts/export_openapi_contract.ps1`; that portability gap has been repaired by resolving Python from `-PythonPath`, `GAIA_PYTHON`, the repo `.venv`, or PATH in a deterministic order.
