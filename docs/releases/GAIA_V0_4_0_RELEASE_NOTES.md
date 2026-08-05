# GAIA v0.4.0 Release Notes

## Summary

GAIA v0.4 adds the controlled workflow foundation for local task records, draft records, approval records, and a deterministic Daily Operations Brief.

The release keeps GAIA local-first and read-only with respect to MicroGrow. Approvals are manual-use decisions only and do not execute actions.

## What Changed

- Task records now support proposed, backlog, ready, in_progress, blocked, awaiting_approval, completed, and cancelled states.
- Draft records now support versioned revisions and enforced `DRAFT - NOT EXECUTED` labeling for Codex prompts.
- Approval records now support explicit decision states, content-hash validation, invalidation on draft changes, and prohibited-action blocking.
- Daily Operations Brief generation now produces a deterministic summary of verified facts, inference, recommendations, warnings, and unknowns.
- CLI, API, Flutter desktop, VS Code task definitions, and workspace validation now expose the workflow foundation.

## Validation

- Python compileall passed.
- Ruff passed.
- mypy passed.
- pytest passed with 49 tests and 1 existing Starlette/httpx warning.
- Flutter pub get passed.
- Flutter analyze passed.
- Flutter test passed.
- Flutter Windows debug build passed.
- Flutter Windows release build passed.
- VS Code workspace validation passed.
- Release-readiness validation passed.

## Live Read-Only Proof

A live read-only MicroGrow scan, snapshot, deterministic question flow, proposed-task creation, draft creation, approval decision, draft revision, and daily brief generation were executed locally.

MicroGrow branch, commit SHA, and porcelain status were unchanged before and after the flow.

## Known Limitations

- Manual GUI smoke steps were not fully exercised in this pass.
- The Starlette/httpx deprecation warning remains upstream.
- Runtime task, draft, approval, and brief data are intentionally local and untracked.

## Safety Notes

- Approval means approved for manual use only.
- Drafts are never executed by GAIA.
- GAIA does not write into MicroGrow.
- GAIA does not add arbitrary shell execution.
