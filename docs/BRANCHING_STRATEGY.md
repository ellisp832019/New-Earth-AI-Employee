# Branching Strategy

## Stable line

- `main` contains stable validated releases only.
- Do not force push to `main`.
- Merge to `main` only after review and acceptance.

## Preservation line

- `gaia-v0.1` preserves the validated read-only inspection foundation.
- Treat it as the baseline branch for the initial GAIA package.

## Development line

- `gaia-v0.2-local-conversational-agent` is the active branch for the conversational agent work.
- Future work should use descriptive branch names such as `gaia-v0.3-windows-dashboard`.

## Rules

- Keep release branches linear and easy to review.
- Avoid rewriting published history.
- Keep feature branches focused on a single package of work.
