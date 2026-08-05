# GAIA v0.3 Handoff

## Planning Goal

GAIA v0.3 should focus on a Windows desktop control centre that wraps the existing v0.2 read-only backend.

## Proposed Branch

- `gaia-v0.3-windows-dashboard`

## Proposed Desktop Surface

- Flutter Windows application.
- First-run setup.
- Backend connection status.
- GAIA health status.
- Ollama model status.
- Project dashboard.
- Conversational chat.
- Evidence viewer.
- Project snapshot viewer.
- Report viewer.
- Agent-run history.
- Codex prompt viewer.
- Settings.
- Audit viewer.
- Approval-centre placeholder.

## Constraints

- Preserve GAIA v0.2 as read-only.
- Do not add external-project write capability.
- Do not add autonomous action loops.
- Do not require Ollama for the core dashboard experience.

## Suggested Milestones

1. Define the desktop shell and backend connection model.
2. Reuse v0.2 API endpoints for health, projects, snapshots, runs, and evidence.
3. Add local state for settings and connection status.
4. Add read-only views for evidence, runs, reports, and audits.
5. Add a future approval-centre placeholder without enabling writes.

## Handoff Notes

The backend work in v0.2 should remain the source of truth. v0.3 should be a presentation and workflow layer, not a rewrite of the evidence and inspection engine.
