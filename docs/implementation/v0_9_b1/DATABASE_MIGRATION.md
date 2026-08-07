# Database Migration

The B1 database schema extends the SQLite store with `project_health_snapshots` and indexes for latest-snapshot lookups.

## Schema version

- previous schema version: `7`
- B1 schema version: `8`

## Migration behaviour

- existing databases are upgraded in place;
- the new table is created if it does not exist;
- indexes are added for project, timestamp, status, and content fingerprint queries;
- old repository and workflow data are preserved.

## Stored health rows

Each row stores:

- snapshot id;
- schema version;
- project identity;
- root;
- configuration fingerprint;
- capture timestamp;
- normalized status;
- normalized payload JSON;
- content fingerprint;
- provenance reference;
- audit event id.
