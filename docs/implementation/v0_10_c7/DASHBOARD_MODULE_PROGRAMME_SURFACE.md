# Dashboard Module Programme Surface

## Purpose

Provide a reusable GAIA-owned read-only programme summary widget surface for downstream dashboard consumption.

## Added Surface

- `GaiaProgrammeSummaryState`
- `GaiaProgrammeSummaryView`
- controller state for programme summary refresh, freshness, and incompatibility handling

## UI Boundary

The module renders read-only programme intelligence only. It does not expose approval, execution, repository mutation, or Codex controls.
