# GAIA v0.4 Known Limitations

## Current Limitations

- The Windows desktop app has been validated with analysis, tests, and builds, but not every live GUI click-through step was exercised in this coding pass.
- The Starlette/httpx deprecation warning remains upstream in FastAPI's test client path.
- Runtime task, draft, approval, brief, and agent-run records are intentionally local-only and untracked by Git.
- Daily brief generation is deterministic and manual; no automatic scheduling is added yet.
- Approvals are manual-use decisions only and do not execute actions.

## Intentional Boundaries

- No arbitrary shell execution was added.
- No MicroGrow write capability was added.
- No execution endpoint was added for tasks, drafts, or approvals.
- No direct New Earth Dashboard database sharing was added.
