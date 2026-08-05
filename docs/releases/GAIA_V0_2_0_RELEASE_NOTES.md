# GAIA v0.2.0 Release Notes

## Release Purpose

GAIA v0.2.0 adds a local, evidence-backed conversational layer to the existing read-only project-control foundation. It keeps GAIA focused on inspection, reporting, and answer generation from local project evidence rather than broad autonomous execution.

## What Changed

- Added a conversational `gaia ask` workflow.
- Added model-provider abstraction with deterministic mock fallback and optional local Ollama access.
- Added agent-run persistence and retrieval.
- Added `/models` and `/agent/*` API endpoints.
- Added `gaia models` and `gaia agent runs` CLI commands.
- Added prompt-injection detection and warning propagation.
- Separated prompt-injection warnings from general answer warnings.
- Redacted the absolute Git host path from conversational evidence.
- Added Codex prompt drafting for planning-only handoff work.
- Added release-hardening and publication-safety documentation.

## Architecture

GAIA v0.2.0 keeps the v0.1 read-only pipeline intact:

- project configuration selects local repositories;
- `ProjectService` still handles scanning, snapshots, search, and reports;
- `AgentService` assembles evidence, classifies the question, and stores the run;
- `ProviderRegistry` chooses between the deterministic mock provider and local Ollama;
- `Database` stores documents, snapshots, audit events, and agent runs in SQLite.

The conversational layer remains evidence-first. Deterministic Git facts come from Git inspection and snapshots, while model output can only summarize or infer from the evidence bundle.

## Security Model

- GAIA remains read-only for the external MicroGrow repository.
- Ollama is optional and loopback-only.
- The release does not introduce any cloud model dependency.
- Runtime databases, logs, caches, and generated reports remain excluded from Git.
- Prompt-injection attempts are detected and surfaced as warnings rather than executed.
- Evidence paths are project-relative where possible.

## CLI Additions

- `gaia models status`
- `gaia models list`
- `gaia ask <project_id> <question>`
- `gaia agent runs list`
- `gaia agent runs show <run_id>`

`gaia ask` supports Markdown or JSON output, safe report destinations, deterministic fallback, and optional refresh of the local repository snapshot.

## API Additions

- `GET /models/status`
- `GET /models`
- `POST /agent/ask`
- `GET /agent/runs`
- `GET /agent/runs/{run_id}`

The existing project, report, search, audit, and health endpoints remain available.

## Deterministic Fallback

If Ollama is unavailable, disabled, missing the configured model, or returns an invalid response, GAIA falls back to the deterministic mock provider or a deterministic answer path. This preserves the v0.1 inspection workflow without requiring local model setup.

## Ollama Behaviour

Ollama support is optional and local-only.

- default endpoint is loopback;
- arbitrary remote URLs are rejected;
- provider status reports unavailable, missing-model, timeout, and error states;
- request and response sizes are bounded.

## Evidence Model

Answers are backed by:

- repository snapshots;
- Git state;
- document search results;
- prompt-injection warnings;
- model/provider status;
- stored agent-run metadata.

The answer contract separates facts, inference, recommendation, and warnings so evidence remains traceable.

## Prompt-Injection Protection

Indexed repository content is treated as untrusted data. GAIA flags common injection phrases, keeps them inert, and never turns repository text into commands or policy.

## Test Results

Release hardening was validated with:

- compileall: passed;
- Ruff: passed;
- mypy: passed;
- pytest: passed with 38 tests and 1 warning;
- `gaia doctor`: passed.

## MicroGrow Read-Only Proof

MicroGrow validation was performed against `D:\Dev\Projects\MicroGrow V1` using read-only inspection, snapshot, search, report, and conversational paths. The branch, commit SHA, and porcelain status matched before and after validation.

## Known Limitations

- Ollama is optional but not bundled.
- The conversational layer is still local and inspection-focused, not a general autonomous agent.
- The release preserves the v0.1 command set, but it does not add write capability to external projects.
- The release stores agent-run history in the local GAIA database only.

## Upgrade Guidance

1. Pull or fetch the `gaia-v0.2-local-conversational-agent` branch.
2. Run `gaia doctor`.
3. Run `gaia models status`.
4. Run `gaia ask microgrow-v1 "Where exactly is MicroGrow currently?" --deterministic-only`.
5. Review `gaia agent runs list`.

## Rollback Guidance

If the conversational layer is not desired, use the validated v0.1 branch or tag and continue running the read-only inspection commands from that baseline. The v0.2 release does not require any external service to preserve v0.1 behaviour.
