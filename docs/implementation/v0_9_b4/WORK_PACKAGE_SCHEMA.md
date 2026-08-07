# Work Package Schema

The schema is stored in SQLite and versioned through `Database.SCHEMA_VERSION = 11`.

## Core tables

- `work_packages`
- `work_package_revisions`
- `work_package_evidence_links`
- `work_package_approval_decisions`
- `work_package_handoffs`
- `work_package_outcomes`

## Important fields

- `semantic_fingerprint` identifies the deterministic package identity;
- `package_fingerprint` and `content_fingerprint` capture the persisted payload;
- `prompt_content_fingerprint` tracks the review prompt text;
- `approval_target_fingerprint` binds the human decision to the exact revision;
- `staleness_state` records whether the package still matches the source evidence.

## Notes

- the package row is the current view;
- the revision row is the immutable change record;
- evidence links are stored separately so they can be audited without re-parsing prompt text.
