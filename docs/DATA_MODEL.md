# Data Model

## `documents`

One row per scanned approved document. Stores path, type, size, timestamp, hash, tracking state, indexing state, warnings and text content.

## `documents_fts`

SQLite FTS5 virtual table used for local full-text retrieval. A `LIKE` fallback is used when FTS5 is unavailable.

## `snapshots`

Stores complete versioned `RepositorySnapshot` JSON payloads. A snapshot records Git state, document counts, warnings and important-path presence.

## `audit_events`

Records application operations with event ID, UTC timestamp, category, operation, project, outcome, safe metadata and error classification.

## Future tables

Later releases may add:

- `agent_runs`;
- `tool_calls`;
- `approvals`;
- `tasks`;
- `decisions`;
- `model_usage`;
- `memory_facts`;
- `report_evidence`.
