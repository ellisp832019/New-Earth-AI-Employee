# Health Normalisation Rules

The B1 health model is intentionally conservative and deterministic.

## Blocked

- project root missing;
- project root unreadable or not traversable;
- Git inspection fails for a Git-backed project;
- release branch requirements are not met when explicitly configured.

## Attention

- tracked or untracked working-tree changes exist;
- the checked-out branch is detached;
- the branch diverges from its upstream;
- required project paths are missing;
- evidence is stale beyond the configured freshness window;
- no upstream exists when a project policy does not allow unknown branch state.

## Unknown

- the project is not Git-backed;
- the upstream state is unknown and the configured policy says to treat it as unknown;
- the evidence set is insufficient to determine a stronger state.
