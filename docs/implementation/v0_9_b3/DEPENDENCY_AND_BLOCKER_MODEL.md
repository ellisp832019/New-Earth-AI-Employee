# Dependency and Blocker Model

B3 models blockers and dependencies explicitly.

## Blockers

- evidence too stale;
- dependency unresolved;
- project root unavailable;
- required human decision missing;
- insufficient evidence.

## Dependencies

- recommendation A can depend on recommendation B;
- a recommendation can depend on evidence refresh before it is actionable;
- higher-order blockers take precedence over narrower follow-up items.

## Safety rule

Dependency cycles fail closed. The engine must not silently sort a cyclic graph.
