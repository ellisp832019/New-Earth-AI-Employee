# Offline Review Packages

GAIA review packages are deterministic archives for offline inspection.

## Allowlisted contents

- package_manifest.json
- hashes.json
- action.json
- approval.json
- receipt.json
- receipt_chain.json
- preview.md
- preview.diff
- source_metadata.json
- verification_instructions.md

## Rules

- deterministic archive ordering;
- normalized names;
- bounded size;
- no credentials;
- no runtime database;
- no executable content;
- no archive traversal;
- no duplicate entries;
- SHA-256 verification.
