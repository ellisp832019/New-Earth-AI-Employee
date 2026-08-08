# Programme Roadmap Model

## Purpose

The roadmap engine combines project health, dependency graph results, change impacts, work packages, release constraints, architecture constraints, and human priorities into a deterministic programme view.

## Expected States

- Now;
- Next;
- Later;
- Blocked;
- Waiting for Evidence;
- Release Candidate;
- Maintenance;
- Experiment.

## Deterministic Scoring Inputs

- critical blocker;
- number of dependent projects;
- release impact;
- safety impact;
- contract impact;
- evidence freshness;
- technical debt severity;
- dependency depth;
- user or business importance;
- readiness;
- coordination complexity.

## Rule

The same evidence must always produce the same ranking. Hidden model-generated scores may explain a result, but they may not override the deterministic ranking.
