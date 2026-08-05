# GAIA v0.4 Acceptance Checklist

## Core Workflow

- [x] Task records exist.
- [x] Task history is recorded.
- [x] Draft records exist.
- [x] Draft revisions are recorded.
- [x] Approval records exist.
- [x] Approval decisions are recorded.
- [x] Draft invalidation on content change works.
- [x] Daily Operations Brief generation works.

## Interfaces

- [x] Task CLI commands work.
- [x] Draft CLI commands work.
- [x] Approval CLI commands work.
- [x] Brief CLI commands work.
- [x] Task API endpoints work.
- [x] Draft API endpoints work.
- [x] Approval API endpoints work.
- [x] Brief API endpoints work.
- [x] Flutter workflow screens are implemented.
- [x] VS Code workspace tasks are validated.

## Safety

- [x] Agent-run tasks start as proposed.
- [x] Approvals are manual-use only.
- [x] Approved content is hash-checked.
- [x] Prohibited approvals are blocked.
- [x] Drafts are labelled `DRAFT - NOT EXECUTED`.
- [x] MicroGrow remains read-only.
- [x] Runtime workflow data is local and untracked.

## Validation

- [x] Python compileall passed.
- [x] Ruff passed.
- [x] mypy passed.
- [x] pytest passed.
- [x] Flutter analyze passed.
- [x] Flutter test passed.
- [x] Flutter Windows debug build passed.
- [x] Flutter Windows release build passed.
- [x] VS Code workspace validation passed.
- [x] Release-readiness validation passed.

## Manual Follow-Up

- [ ] Complete any remaining interactive desktop smoke steps if Peter wants a final GUI pass before merge.
