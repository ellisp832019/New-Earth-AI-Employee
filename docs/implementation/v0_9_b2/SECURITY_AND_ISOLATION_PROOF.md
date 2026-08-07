# Security and Isolation Proof

B2 keeps the same read-only boundary as B1.

## Guarantees

- no writes to MicroGrow;
- no writes to the New Earth Dashboard;
- no arbitrary shell execution;
- no cross-project mutation;
- no automatic Codex execution;
- no autoupdate of external evidence sources.

## Enforcement

- comparisons run only against canonical GAIA health snapshots;
- cross-project comparisons fail closed;
- findings are stored in GAIA-owned SQLite tables only;
- semantic fingerprints prevent repeated noise from resurfacing as new evidence.
