# GAIA v0.3 Handoff

## Planning Goal

GAIA v0.3 focused on a Windows desktop control centre that wraps the existing v0.2 read-only backend.

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

## Delivered

1. Flutter Windows shell with read-only navigation and status chips.
2. Backend connection and first-run setup for the local loopback backend.
3. Read-only views for projects, evidence, snapshots, reports, agent runs, audit events, and settings.
4. Prompt draft view for the existing conversational workflow.
5. Dedicated desktop setup, run, test, build, and validation scripts.

## Handoff Notes

The backend work in v0.2 remains the source of truth. v0.3 is a presentation and workflow layer, not a rewrite of the evidence and inspection engine.
