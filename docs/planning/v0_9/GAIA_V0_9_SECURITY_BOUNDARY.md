# GAIA v0.9 Security Boundary

## Required Guarantees

- GAIA backend remains the source of truth.
- Dashboard does not read GAIA SQLite.
- Dashboard does not access MicroGrow.
- Dashboard remains read-only.
- output execution stays in the GAIA Control Centre.
- rollback stays in the GAIA Control Centre.
- retention application stays in the GAIA Control Centre.
- signing-key management stays in the GAIA Control Centre.
- no arbitrary shell execution.
- no automatic Codex execution.
- no cloud fallback without explicit configuration.
- no telemetry by default.
- no automatic model download.
- no autonomous Git operations.
- no external writes without explicit authority.

## Planning Implication

Any v0.9 feature must be designed so it can be reviewed, approved, and rolled back before it changes repository state.
