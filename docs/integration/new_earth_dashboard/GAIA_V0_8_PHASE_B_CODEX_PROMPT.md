# GAIA v0.8 Phase B Codex Prompt

You are continuing from the GAIA v0.8 Phase A audit.

## Baselines

- GAIA repository: `D:\Dev\Projects\New-Earth-AI-Employee`
- GAIA branch: `gaia-v0.8-new-earth-dashboard-integration-audit`
- GAIA baseline SHA: `cd889be8e7f10a4c7105b6f72d52361aea33b31b`
- Dashboard repository: `D:\Dev\Projects\New Earth - Command Dashboard`
- Dashboard branch: `feat/asset-intelligence-tab`
- Dashboard baseline SHA: `60d15a88d55bf263d749724d911bb3e4c8592d94`
- MicroGrow repository: `D:\Dev\Projects\MicroGrow V1`
- MicroGrow branch: `planning/microgrow-v1-firmware-target-dependency-lock`
- MicroGrow baseline SHA: `0f9df32862bfb74f0acba8c4c1aa84d5a17c8363`

## Instructions

1. Create a dedicated integration branch in the Dashboard repository.
2. Create and verify a backup before any write operation in the Dashboard repository.
3. Preserve all existing Dashboard work.
4. Implement only the approved architecture from the GAIA audit.
5. Consume the official GAIA packages and keep the GAIA backend as the single source of truth.
6. Do not duplicate backend logic, database state, signing logic, retention logic, or receipt verification in the Dashboard.
7. Do not read GAIA SQLite directly.
8. Do not access MicroGrow directly.
9. Keep the GAIA embedded surface read-only.
10. Add and run the complete Dashboard and GAIA validation suite.
11. Commit the work.
12. Push the branch.
13. Open a PR.
14. Stop before merge.

## Required Architecture

- Preferred route location: `/more/ai-employee`
- Preferred integration shape: a thin Dashboard-owned adapter around the official GAIA Flutter packages
- Fallback: process-isolated or deep-link integration with the standalone GAIA Control Centre
- Feature flag: disabled by default until the route and adapter are stable
- Cache policy: preserve the last good state and label stale data
- Trust surface: read-only summaries only

## Safety Rules

- Never write into the MicroGrow repository.
- Never turn this audit into a direct GAIA backend clone.
- Never expose signing private keys.
- Never make the embedded GAIA surface perform actions.
- Never auto-merge the PR.
