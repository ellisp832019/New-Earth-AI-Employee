# Degraded Mode Evidence

The governance client degrades deterministically when NEOS is unavailable or incompatible.

## Observed Fallbacks

- unavailable source -> UNKNOWN readiness
- timeout -> unavailable source state
- malformed payload -> unavailable source state
- schema mismatch -> unavailable source state
- governance version mismatch -> unavailable source state

## Cache Semantics

- fresh cache is local consumer history
- stale cache is local consumer history
- no cache stays distinct from live source truth
