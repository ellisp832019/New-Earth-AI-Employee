# GAIA v0.9 Change Intelligence Model

## Inputs

- project snapshots;
- Git branch and HEAD state;
- working-tree status;
- test results;
- dependency state;
- release metadata;
- documentation freshness;
- backend and package version state.

## Change Classes

- snapshot delta;
- branch divergence;
- release drift;
- contract drift;
- documentation drift;
- stale evidence;
- untracked work;
- dependency drift;
- test regression.

## Output

Each finding should include:

- what changed;
- why it matters;
- evidence source;
- freshness;
- severity;
- confidence;
- suggested next action.

## Design Rule

Change intelligence should highlight only meaningful changes, not every low-value file delta.
