# Database Migration

B2 extends the SQLite schema with comparison and finding tables.

## Schema version

- previous schema version: `8`
- B2 schema version: `9`

## New tables

- `project_change_comparisons`
- `project_change_findings`

## Migration behaviour

- clean databases create the new tables directly;
- existing B1 databases are upgraded in place;
- v0.8-era databases are also upgraded through the repository migration path;
- existing health and workflow tables are preserved.

## Query support

- latest comparison by project;
- comparison by ID;
- findings by project;
- findings by comparison;
- recent findings across enabled projects;
- portfolio-style summaries.
