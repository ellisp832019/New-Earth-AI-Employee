# Migration and Compatibility Plan

## Storage Direction

Prefer a small set of normalized canonical records with revision history over duplicating derived state everywhere.

## Candidate New Entities

- project_contracts;
- architecture_entities;
- architecture_relationships;
- change_proposals;
- programme_snapshots;
- programme_recommendations;
- release_trains;
- programme_packages;
- programme_package_revisions;
- programme_decisions.

## Compatibility Rule

v0.9 projects, snapshots, recommendations, work packages, API consumers, integration client consumers, Windows Control Centre, and Dashboard integration must remain usable.

## Maintenance Note

The package-version pressure seen in v0.9 validation should be treated as a separate maintenance decision, not as a broad upgrade wave inside the architecture PRs.
