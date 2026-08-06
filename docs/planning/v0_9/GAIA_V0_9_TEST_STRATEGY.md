# GAIA v0.9 Test Strategy

## Test Layers

- backend unit tests;
- API contract tests;
- data-model and migration tests;
- change-intelligence tests;
- prioritisation tests;
- work-package lifecycle tests;
- approval-state tests;
- Windows UI tests;
- Dashboard read-only summary tests;
- release-readiness and packaging scripts.

## Required Behaviours

- deterministic recommendations;
- explainable scores;
- no automatic execution;
- no cross-project write leakage;
- preserved backward compatibility with v0.8.

## Evidence Expectations

Tests should capture:

- why a recommendation exists;
- why it is ranked that way;
- what makes it stale or blocked;
- what prevents execution.
