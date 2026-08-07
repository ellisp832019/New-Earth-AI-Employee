# Noise Filtering and Fingerprinting

The B2 comparison layer filters low-value differences before they become findings.

## What is ignored

- snapshot IDs by themselves;
- capture timestamps by themselves;
- audit event timestamps by themselves;
- generated record IDs by themselves.

## What is used

- B1 project-health content fingerprints;
- project configuration fingerprints;
- normalized Git state;
- important-path presence;
- evidence-freshness state.

## Result

If two snapshots are semantically identical, B2 records the comparison but emits no noisy findings.
