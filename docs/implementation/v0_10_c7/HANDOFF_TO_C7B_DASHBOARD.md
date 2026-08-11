# Handoff to C7B Dashboard

## C7A Merge-Pin Rule

- C7A validated implementation head before merge: `06c8d210470486fe95e08184729912adfb9782ca`
- This SHA is for evidence and traceability only.
- PR #30 must be merged before C7B begins.
- After PR #30 is merged, C7B must determine the exact resulting C7A merge commit on GAIA `main`.
- The New Earth Dashboard must pin both GAIA Git dependencies to that exact merged-`main` SHA.
- Do not pin a floating branch.
- Do not use `main` as an unpinned Git ref.
- Do not continue using the old `dc6f6ba1c186a461d3d5627e5d3af75625cda6fe` pre-repair SHA as the authoritative C7B consumer pin.
- The C7B Dashboard worktree must verify that the selected SHA exists on GAIA `main` before changing `pubspec` dependencies.

## Available GAIA Public Surfaces

- public programme API routes;
- CLI read commands;
- integration-client programme models and methods;
- reusable dashboard-module programme summary view.

## Dashboard Consumer Requirements

- consume the reviewed merged GAIA SHA determined after PR #30 is merged;
- use the public read-only programme contract;
- keep the Dashboard repository read-only in C7A;
- do not use floating branch references;
- preserve fail-closed handling for unavailable or incompatible backend responses.

## Required Tests

- Dashboard render coverage for programme summary;
- Dashboard failure-state coverage for unavailable and incompatible backend responses;
- integration-client and API contract checks against the pinned GAIA SHA.

## Forbidden Actions

- approval;
- rejection;
- handoff execution;
- repository mutation;
- Codex execution;
- Git mutation;
- release publication.

## Suggested Dashboard Branch

- `feature/gaia-v0.10-c7-programme-summary`

## Dependency Ordering

1. Merge the GAIA C7A PR.
2. Determine the exact merged-main GAIA SHA after PR #30 lands.
3. Verify that SHA exists on GAIA `main` before updating Dashboard pins.
4. Pin the Dashboard worktree to that merged-main SHA.
5. Implement the Dashboard read-only programme summary integration in its own branch.
