# GAIA v0.9 Implementation Phases

## Phase B1: Multi-Project Registry and Project-Health Model

- Scope: canonical project records, health snapshots, and state normalization.
- Dependencies: existing project registry, scanning, snapshots, repository inspection.
- Tests: project-health and isolation tests.
- Acceptance gate: a project snapshot can be produced and queried deterministically.
- Rollback: retain v0.8 behavior and disable v0.9 registry surfaces.
- Suggested branch: `planning/gaia-v0.9-b1-multi-project-registry`

## Phase B2: Snapshot Comparison and Change Intelligence

- Scope: snapshot diffs, drift detection, stale evidence, branch divergence.
- Dependencies: B1.
- Tests: diff and drift tests.
- Acceptance gate: meaningful changes are identified with evidence.
- Rollback: hide the change-intelligence API and UI.
- Suggested branch: `planning/gaia-v0.9-b2-change-intelligence`

## Phase B3: Recommendation and Deterministic Prioritisation Engine

- Scope: ranking, explainable scoring, dependency-aware recommendations.
- Dependencies: B2.
- Tests: scoring and ranking tests.
- Acceptance gate: recommended work items are explainable and deterministic.
- Rollback: return to non-ranked summaries.
- Suggested branch: `planning/gaia-v0.9-b3-prioritisation-engine`

## Phase B4: Human-Reviewable Work-Package Builder

- Scope: work packages, revisions, prompts, approval states.
- Dependencies: B3.
- Tests: package lifecycle and approval tests.
- Acceptance gate: a full work package can be proposed and reviewed without execution.
- Rollback: disable package creation surfaces.
- Suggested branch: `planning/gaia-v0.9-b4-work-package-builder`

## Phase B5: Windows Project Officer Workspace

- Scope: Control Centre UI for the new planning workflows.
- Dependencies: B1-B4.
- Tests: Windows UI and accessibility tests.
- Acceptance gate: the Control Centre can review and hand off work packages.
- Rollback: keep v0.8 UI only.
- Suggested branch: `planning/gaia-v0.9-b5-project-officer-ui`

## Phase B6: API, CLI and Integration-Client Compatibility

- Scope: versioned API, CLI commands, client updates.
- Dependencies: B1-B5.
- Tests: API, CLI, and package compatibility tests.
- Acceptance gate: API and client remain deterministic and backward-aware.
- Rollback: keep v0.8 endpoints and client surfaces.
- Suggested branch: `planning/gaia-v0.9-b6-api-cli-client`

## Phase B7: Read-Only Dashboard Summary Expansion

- Scope: read-only summary surfaces for portfolio and recommendations.
- Dependencies: B6.
- Tests: Dashboard read-only tests.
- Acceptance gate: Dashboard shows summaries only.
- Rollback: keep the v0.8 employee surface only.
- Suggested branch: `planning/gaia-v0.9-b7-dashboard-summaries`

## Phase B8: Cross-Repository Acceptance and Release Closeout

- Scope: final audit, evidence, and release documentation.
- Dependencies: B7.
- Tests: release-readiness and cross-repository checks.
- Acceptance gate: planning artifacts and release evidence are complete.
- Rollback: stop before tag or publication.
- Suggested branch: `planning/gaia-v0.9-b8-acceptance-closeout`
