# Security Boundary Proof

## Prohibited Paths

The C6 workspace does not provide:

- Codex execution;
- arbitrary shell execution;
- Git execution;
- repository writes;
- release publication;
- deployment;
- hardware control;
- messaging;
- model downloads;
- cloud fallback.

## Boundary Enforcement

- backend logic remains canonical in Python;
- Flutter only renders the backend payload;
- the internal workspace route is hidden from the public OpenAPI schema;
- no direct SQLite access exists in Flutter;
- Dashboard and MicroGrow remain read only.
