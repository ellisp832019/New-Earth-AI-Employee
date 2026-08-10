# GAIA Governance Context v1

GAIA Governance Context v1 is a downstream consumer of NEOS governance output.

## Authority Boundary

- Platform Core declares architecture and ownership.
- NEOS observes and reconciles the engineering estate.
- GAIA interprets NEOS governance findings for prioritisation, review and work-package preparation.

## What GAIA Stores

- Source facts from NEOS governance snapshots and findings.
- Separate GAIA interpretation: explanation, priority, recommended review questions, and suggested next actions.
- Deterministic preview records for work-package preparation.

## What GAIA Does Not Do

- It does not recreate NEOS governance rules.
- It does not rewrite NEOS source fields.
- It does not claim canonical engineering authority.
- It does not mutate NEOS source state.

## Surfaces

- `GET /governance`
- `GET /governance/status`
- `GET /governance/findings`
- `GET /governance/project/{project_id}`
- `GET /governance/snapshot`
- `gaia governance ...`

## Notes

The live GAIA README and the governance context service should be kept consistent with this boundary.
