# Handoff to C7B Dashboard

## Final GAIA SHA

- `dc6f6ba1c186a461d3d5627e5d3af75625cda6fe`

## Available GAIA Public Surfaces

- public programme API routes;
- CLI read commands;
- integration-client programme models and methods;
- reusable dashboard-module programme summary view.

## Dashboard Consumer Requirements

- consume the reviewed GAIA SHA above;
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
2. Pin the Dashboard worktree to the reviewed GAIA SHA above.
3. Implement the Dashboard read-only programme summary integration in its own branch.
