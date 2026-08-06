# GAIA v0.8.0 Cross-Repository Acceptance

## Scope

This document records the evidence that GAIA v0.8.0 was accepted across the GAIA repository, the New Earth Dashboard integration, and the read-only MicroGrow proof.

## GAIA Baseline

- Repository: `D:\Dev\Projects\New-Earth-AI-Employee`
- Branch: `release/gaia-v0.8.0-cross-repository-acceptance`
- Starting SHA: `b1a23b892fab412121f691d31407c075583f0da4`
- Baseline release tag: `gaia-v0.7.0`
- `gaia-v0.7.0` exists and is published.
- `gaia-v0.8.0` did not exist at preflight time.

## Dashboard Acceptance Evidence

- Dashboard PR #3: merged.
  - Title: `Integrate GAIA v0.8 read-only dashboard surface`
  - Head branch: `integration/gaia-v0.8-ai-employee`
  - Merge SHA: `730046db9facf55d33da826c08a01ce666a7650f`
- Dashboard PR #4: merged.
  - Title: `Fix GAIA v0.8 Windows startup and analyzer regressions`
  - Head SHA: `a0e816d76879f34e18dd1e1be15457261f15df73`
  - Merge SHA: `aeb8dcc38b52316aa53660b9af9523cc1b41eddf`
- Final accepted Dashboard main SHA: `aeb8dcc38b52316aa53660b9af9523cc1b41eddf`

## MicroGrow Proof

- Repository: `D:\Dev\Projects\MicroGrow V1`
- Branch: `planning/microgrow-v1-firmware-target-dependency-lock`
- SHA: `0f9df32862bfb74f0acba8c4c1aa84d5a17c8363`
- Commands were read-only and showed no change in branch, HEAD, or working-tree diff state.

## Acceptance Statement

The GAIA v0.8 Dashboard integration was verified as accepted after PR #3 and PR #4 merged into the Dashboard main branch. The GAIA repository then recorded the release-closeout evidence without modifying Dashboard or MicroGrow.
