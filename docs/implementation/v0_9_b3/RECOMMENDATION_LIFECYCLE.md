# Recommendation Lifecycle

Recommendation state is deterministic and auditable.

## States

- `active`;
- `blocked`;
- `deferred`;
- `resolved`;
- `superseded`;
- `stale`.

## Transition rules

- active recommendations can become resolved when the supporting issue disappears;
- stale evidence can move recommendations into blocked state until a refresh happens;
- higher-order project-health blockers can supersede narrower recommendations;
- unchanged evidence keeps the recommendation stable across repeated refreshes.

## Queue rule

Blocked items stay visible in the queue. They are not hidden just because they are not yet actionable.
