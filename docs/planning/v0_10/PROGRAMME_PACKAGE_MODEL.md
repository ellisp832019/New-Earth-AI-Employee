# Programme Package Model

## Purpose

A Programme Package groups several project-level work packages under one coordinated objective.

## Canonical Fields

- `programme_package_id`
- `objective`
- `projects_involved`
- `project_work_packages`
- `dependency_order`
- `change_impact_evidence`
- `architecture_references`
- `risks`
- `global_acceptance_criteria`
- `per_project_acceptance_criteria`
- `rollback_coordination`
- `release_sequence`
- `human_approval`
- `revision_history`
- `provenance`

## Lifecycle

The package should support explicit review states such as proposed, under_review, approved, rejected, superseded, expired, handed_off, partially_completed, completed, failed, and rolled_back.

## Rule

It does not execute child work packages. It only coordinates them for human review and approval.
