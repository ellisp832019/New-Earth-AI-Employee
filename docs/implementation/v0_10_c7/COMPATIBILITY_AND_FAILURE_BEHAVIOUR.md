# Compatibility and Failure Behaviour

## Compatibility

- existing v0.9 read surfaces remain available;
- the C6 internal workspace route remains internal;
- public programme routes are additive.

## Failure Handling

- unavailable backends fail closed;
- incompatible payloads are reported explicitly;
- stale evidence remains visible as stale;
- unknown state is preserved instead of being coerced to healthy.
