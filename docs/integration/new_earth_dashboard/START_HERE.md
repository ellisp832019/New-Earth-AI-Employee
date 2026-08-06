# Start Here

## What Was Audited

This audit reviewed how the released GAIA v0.7 packages can be safely integrated into the real New Earth Dashboard.

## Baselines

- GAIA: `gaia-v0.8-new-earth-dashboard-integration-audit` at `cd889be8e7f10a4c7105b6f72d52361aea33b31b`
- Dashboard: `feat/asset-intelligence-tab` at `60d15a88d55bf263d749724d911bb3e4c8592d94`
- MicroGrow: `planning/microgrow-v1-firmware-target-dependency-lock` at `0f9df32862bfb74f0acba8c4c1aa84d5a17c8363`

## Recommended Reading Order

1. `V0_8_GAIA_PREFLIGHT.md`
2. `DASHBOARD_REPOSITORY_BASELINE.md`
3. `DASHBOARD_TECHNOLOGY_AND_BUILD_MAP.md`
4. `DASHBOARD_ARCHITECTURE_ATLAS.md`
5. `DASHBOARD_ROUTE_AND_NAVIGATION_MAP.md`
6. `DASHBOARD_STATE_AND_DATA_FLOW_MAP.md`
7. `GAIA_INTEGRATION_SURFACE_MAP.md`
8. `GAIA_INTEGRATION_GAP_MATRIX.md`
9. `DASHBOARD_GAIA_SECURITY_BOUNDARY.md`
10. `GAIA_INTEGRATION_OPTIONS.md`
11. `RECOMMENDED_GAIA_DASHBOARD_ARCHITECTURE.md`
12. `GAIA_V0_8_PHASE_B_IMPLEMENTATION_PLAN.md`
13. `GAIA_V0_8_ACCEPTANCE_CRITERIA.md`
14. `GAIA_V0_8_PHASE_B_CODEX_PROMPT.md`
15. `READ_ONLY_BOUNDARY_PROOF.md`

## Primary Recommendation

Use a thin Dashboard-owned adapter around the official GAIA packages and land the surface under `/more/ai-employee`.

## Major Blockers

- The Dashboard repository is dirty and already has active unrelated work.
- The Dashboard repository also drifted during the audit, so a fresh baseline capture is required before any Phase B writes.
- Phase B must start in a separate Dashboard integration branch.
- The embedded GAIA surface must remain read-only.
- No GAIA backend or signing logic should be recreated in the Dashboard.

## Readiness Classification

`ready_with_conditions`

## Exact Next Action

Create the Dashboard integration branch, capture a verified backup, and then implement the adapter and route plan from the recommended architecture.
