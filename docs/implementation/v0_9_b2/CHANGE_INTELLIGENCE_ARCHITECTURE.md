# Change Intelligence Architecture

B2 introduces an internal change-intelligence service that sits beside the B1 project-health service.

## Inputs

- historical project-health snapshots;
- snapshot content fingerprints;
- project configuration fingerprints;
- Git branch, HEAD, upstream, and working-tree state;
- important-path presence;
- evidence freshness state.

## Responsibilities

- compare two snapshots deterministically;
- persist a comparison record;
- persist findings only when a meaningful change exists;
- deduplicate semantic repeats;
- expose query helpers for comparisons, findings, and portfolio summaries;
- preserve the original snapshot records as immutable evidence.

## Design constraints

- no B3 prioritisation;
- no automatic execution;
- no cross-project writes;
- no Dashboard contract expansion.
