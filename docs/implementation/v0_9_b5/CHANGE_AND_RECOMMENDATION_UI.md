# Change and Recommendation UI

The change and recommendation panels are derived from backend data only.

## Change intelligence

- project;
- type;
- severity;
- direction;
- confidence;
- before/after summary;
- reason codes;
- evidence references;
- freshness;
- capture timestamp.

## Recommendations

- priority tier;
- deterministic score;
- scoring breakdown;
- title and rationale;
- blockers and dependencies;
- reasons to proceed;
- reasons not to proceed;
- freshness and lifecycle state.

## UI rule

The Flutter layer must not recalculate detector output or score results.

