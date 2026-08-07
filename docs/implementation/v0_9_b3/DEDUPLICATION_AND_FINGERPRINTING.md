# Deduplication and Fingerprinting

B3 avoids repeated recommendation spam by using semantic fingerprints.

## What is ignored

- record IDs by themselves;
- evaluation timestamps by themselves;
- repeated refreshes with the same evidence and policy.

## What is used

- recommendation policy version;
- project ID;
- recommendation type;
- issue key;
- source finding IDs;
- source comparison IDs;
- source snapshot IDs;
- evidence fingerprints;
- dependency identity.

## Result

The same evidence and policy version produce the same recommendation identity and score.
