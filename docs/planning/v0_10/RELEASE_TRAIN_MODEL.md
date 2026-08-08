# Release Train Model

## Purpose

Release trains coordinate several project releases that must move together because of shared contracts, dependencies, or release constraints.

## Canonical Fields

- `release_train_id`
- `objective`
- `participating_projects`
- `required_versions`
- `dependency_order`
- `compatibility_constraints`
- `blocking_evidence`
- `required_tests`
- `rollback_relationships`
- `release_readiness`
- `human_approval_state`

## Rule

Release-train approval must never publish releases automatically. It only prepares a coordinated human decision.
