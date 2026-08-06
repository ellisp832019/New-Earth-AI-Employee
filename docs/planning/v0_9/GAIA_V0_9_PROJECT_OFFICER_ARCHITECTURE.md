# GAIA v0.9 Project Officer Architecture

## Architecture Summary

GAIA v0.9 should add a project officer layer on top of the existing backend services:

- project registry and inspection primitives remain the source of truth;
- project-health snapshots collect normalized status;
- change-intelligence services compare snapshots and release evidence;
- prioritisation services rank candidate work items deterministically;
- work-package services assemble reviewable packets and Codex prompts;
- approval services enforce human gatekeeping;
- the Control Centre presents the workflow;
- the Dashboard consumes read-only summaries only.

## Suggested Layers

| Layer | Responsibility |
| --- | --- |
| Inspection | Read repository state, release state, test state, documentation state, and evidence freshness. |
| Normalization | Convert raw repository data into versioned project-health snapshots. |
| Diff / drift | Compare snapshots and identify meaningful changes. |
| Scoring | Rank items with deterministic, explainable criteria. |
| Packaging | Build human-reviewable work packages and prompts. |
| Governance | Track approval states, handoffs, expiries, and outcomes. |
| Presentation | Render the Control Centre and read-only Dashboard summaries. |

## Key Rule

The architecture may assist with planning, but it must never become an autonomous repository-changing agent.
