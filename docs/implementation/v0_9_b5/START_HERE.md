# GAIA v0.9 B5 Windows Project Officer Workspace

B5 adds the Windows Control Centre surfaces for reviewing the planning pipeline built in B1-B4.

## Scope

- portfolio summaries for project health, change intelligence, recommendations, and work packages;
- project-level review of health snapshots, change findings, recommendation state, revision history, and provenance;
- generated prompt review with explicit human approval, rejection, handoff, staleness, and expiry controls;
- read-only inspection only, with no Codex execution and no external repository writes.

## Non-goals

- no B6 API or CLI compatibility work;
- no version bump from `0.8.0`;
- no Dashboard writes, MicroGrow writes, or autonomous work execution.

## Validation targets

- backend checks: `ruff`, `mypy`, `pytest`;
- Flutter checks: `flutter analyze`, `flutter test`, `flutter build windows --release`;
- repository validation: release readiness, dashboard conformance, integration contract, and smoke test evidence.

## Read next

1. [Project Officer UI Architecture](PROJECT_OFFICER_UI_ARCHITECTURE.md)
2. [Navigation and Information Architecture](NAVIGATION_AND_INFORMATION_ARCHITECTURE.md)
3. [Portfolio and Project Health UI](PORTFOLIO_AND_PROJECT_HEALTH_UI.md)
4. [Change and Recommendation UI](CHANGE_AND_RECOMMENDATION_UI.md)
5. [Work Package Review UI](WORK_PACKAGE_REVIEW_UI.md)
6. [Approval and Handoff UI](APPROVAL_AND_HANDOFF_UI.md)
7. [Codex Prompt Review Boundary](CODEX_PROMPT_REVIEW_BOUNDARY.md)
8. [Accessibility and Windows Layout](ACCESSIBILITY_AND_WINDOWS_LAYOUT.md)
9. [Security and Authority Proof](SECURITY_AND_AUTHORITY_PROOF.md)
10. [Validation Evidence](VALIDATION_EVIDENCE.md)
11. [Handoff to B6](HANDOFF_TO_B6.md)
