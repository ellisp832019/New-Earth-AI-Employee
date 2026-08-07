# Change Finding Model

Each finding stores the evidence needed for a human reviewer to understand the comparison.

## Identity

- finding ID;
- schema version;
- project ID;
- finding type;
- comparison ID;
- capture timestamp.

## Classification

- change class;
- severity;
- direction;
- confidence;
- status.

## Explanation

- concise deterministic summary;
- what changed;
- why it matters;
- affected evidence fields.

## Evidence

- before value where safe;
- after value where safe;
- source evidence references;
- freshness information.

## Provenance

- deterministic content fingerprint;
- detector version;
- audit reference where available.
