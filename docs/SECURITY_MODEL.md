# Security Model

## Threats considered

- path traversal and absolute-path escape;
- symlink or junction escape;
- access to credentials and environment files;
- binary or oversized file ingestion;
- prompt injection contained in project documents;
- arbitrary command execution;
- credential leakage in Git remote URLs;
- accidental mutation of the inspected repository;
- audit logs containing sensitive contents.

## Controls

- canonical `resolve(strict=True)` path resolution;
- common-root validation with Windows case normalisation;
- approved extension list;
- excluded directory and filename lists;
- broad secret-bearing filename detection;
- symlink avoidance during scans;
- no `shell=True` usage;
- fixed Git argument templates only;
- command timeout and output limits;
- remote credential redaction;
- pre/post repository-state comparison;
- audit metadata excludes file contents and secrets;
- fail-closed behaviour when a path cannot be proven safe.

## Prompt injection boundary

Repository text is **data**, never authority. Later language-model integration must wrap retrieved excerpts as untrusted evidence and must not permit document text to alter employee policies, tool permissions or approval requirements.

## Remaining limitations

- Windows junction detection depends on operating-system behaviour and Python path resolution.
- Read-only access is enforced by application policy; production deployment should also use Windows filesystem permissions or a dedicated restricted account.
- SQLite audit records are append-oriented but not cryptographically immutable. Hash chaining is planned for a later release.
