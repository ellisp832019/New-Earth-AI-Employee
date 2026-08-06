# GAIA v0.8 Current Capability Matrix

## Released Capabilities

| Area | Current state | Notes |
| --- | --- | --- |
| Project registry | Implemented | Approved project definitions, allowlists, excluded paths, and per-project metadata exist. |
| Snapshot capture | Implemented | Repository snapshots and derived reports are already supported. |
| Retrieval and scanning | Implemented | Local document scanning, search, and evidence ranking exist. |
| Tasks and drafts | Implemented | Controlled tasks, drafts, approvals, and manual review flows exist. |
| Agent runs | Implemented | Read-only conversational runs and evidence-backed responses exist. |
| Permission manifests | Implemented | GAIA-owned output permissions and previews exist. |
| Action templates | Implemented | Versioned action templates and previews exist. |
| Execution receipts | Implemented | Receipts, verification, and chain summaries exist. |
| Rollback records | Implemented | Rollback support is modeled and recorded in GAIA. |
| Provenance | Implemented | Manifest creation, inspection, and verification exist. |
| Signing lifecycle | Implemented | Local signing key lifecycle exists in the Control Centre. |
| Trust alerts | Implemented | Trust and provenance warnings are visible through the backend and UI. |
| Retention | Implemented | Retention policy and report scaffolding exist. |
| Integration client | Implemented | Official Dart client package exists. |
| Dashboard module | Implemented | Official read-only embedded module exists. |
| Windows Control Centre | Implemented | The desktop app provides the main operational surface. |
| Dashboard integration | Implemented | Read-only GAIA employee surface exists under `/more/ai-employee`. |

## Partially Implemented or Narrow

| Area | Current state | Notes |
| --- | --- | --- |
| Project officer intelligence | Partial | The backend has evidence sources, but not a dedicated project officer reasoning layer. |
| Change intelligence | Partial | Snapshots and Git inspection exist, but there is no unified change-detection engine. |
| Recommendation intelligence | Partial | The system can summarize and guide, but not yet produce structured prioritized work plans. |
| Work packages | Partial | Receipts, manifests, and prompt drafting exist, but not a first-class work-package lifecycle. |
| Multi-project orchestration | Partial | Projects are supported individually, but not yet as a full portfolio intelligence model. |
| Dashboard summaries for v0.9 | Not yet | The Dashboard only exposes the v0.8 read-only employee surface. |

## Missing or Explicitly Absent

| Area | Status | Notes |
| --- | --- | --- |
| Autonomous execution | Absent | Must remain out of scope. |
| Automatic Codex invocation | Absent | Must remain manual and human-approved. |
| Autonomous repository mutation | Absent | Must remain out of scope. |
| Generic unrestricted filesystem access | Absent | Project allowlists remain required. |
| Direct Dashboard database ownership of GAIA | Absent | Dashboard stays read-only. |
