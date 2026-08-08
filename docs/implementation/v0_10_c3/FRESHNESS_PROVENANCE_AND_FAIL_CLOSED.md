# Freshness, Provenance, and Fail-Closed Aggregation

## Freshness

The result cannot be fresher than its weakest critical evidence.

If a target, contract, or dependency path is stale or unavailable, the result reflects that condition.

## Provenance

The result preserves the provenance chain of the canonical evidence used for the analysis.

Generated analysis timestamps are metadata only and do not participate in semantic identity.

## Fail-Closed Rule

The analysis never upgrades:

- unknown to safe;
- stale to current;
- unavailable to unaffected;
- unresolved to verified.

If the canonical evidence is incomplete, the result reports that incompleteness explicitly.
