# GAIA v0.9 Data Model Plan

## New Versioned Models

- project health snapshots;
- detected changes;
- drift findings;
- recommendations;
- work queues;
- work packages;
- work-package revisions;
- approval decisions;
- handoff records;
- completion evidence.

## Database Plan

- extend the existing backend schema with new versioned tables;
- add migrations rather than replacing tables in place;
- add indexes for project ID, status, freshness, and priority queries;
- keep retention rules explicit for planning artifacts;
- preserve existing v0.8 tables and API responses.

## Compatibility Rule

New planning records must not break the released v0.8 Dashboard integration.
