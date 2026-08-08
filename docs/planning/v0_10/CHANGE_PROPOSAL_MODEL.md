# Change Proposal Model

## Purpose

A Change Proposal records a potential engineering change before it is implemented.

## Canonical Fields

- `proposal_id`
- `title`
- `origin_project`
- `objective`
- `change_type`
- `target_entities`
- `proposed_contract_changes`
- `affected_versions`
- `evidence`
- `impact_result`
- `risk`
- `blocked_by`
- `depends_on`
- `required_validation`
- `rollback_concept`
- `recommended_order`
- `status`
- `revision`
- `human_decision`

## Lifecycle

- proposed;
- under_review;
- approved;
- rejected;
- superseded;
- expired;
- handed_off.

## Rule

Approval freezes the revision. A later edit is a new revision and requires a new human review.
