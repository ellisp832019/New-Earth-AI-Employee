# Revision Model

Each work package has a revision history.

## Rules

- revision `1` is created with the initial package;
- later revisions are created from the current revision plus a change reason;
- a revision is immutable once written;
- the package record points to the current revision only;
- a revision approval does not transfer to future revisions.

## Revision data

- changed fields;
- change reason;
- approval state at creation;
- staleness state at creation;
- generated prompt snapshot;
- revision fingerprint and approval target fingerprint.
