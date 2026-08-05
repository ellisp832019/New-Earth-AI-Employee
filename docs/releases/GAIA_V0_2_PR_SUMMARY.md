# GAIA v0.2 PR Summary

## Title

GAIA v0.2 - Local evidence-backed conversational project officer

## Summary

This pull request prepares GAIA v0.2.0 for release review. It adds a local conversational layer on top of the existing read-only project-control foundation while preserving the v0.1 inspection workflow.

## What v0.2 Adds

- `gaia ask` for evidence-backed questions.
- mock and optional Ollama model-provider support.
- agent-run storage and inspection.
- model status commands.
- API endpoints for conversational use and run history.
- Codex prompt drafting for planning handoffs.
- prompt-injection and evidence-path hardening.

## What Remains Read-Only

- MicroGrow remains an external read-only source.
- GAIA does not add shell execution, email, calendar, device control, or external project writes.
- Deterministic Git inspection still uses fixed read-only commands.

## Architecture Additions

- `AgentService` orchestrates classification, retrieval, evidence ranking, and answer composition.
- `ProviderRegistry` abstracts model backends.
- `Database` stores agent runs alongside existing document and snapshot data.
- CLI and FastAPI surfaces expose conversational features without introducing mutating project endpoints.

## Security and Safety

- Ollama is loopback-only and optional.
- Cloud model fallback is not used.
- Prompt-injection phrases are detected and recorded as warnings.
- Evidence paths are project-relative where possible.
- Runtime databases and report artifacts remain excluded from Git.

## Verification

- compileall passed.
- Ruff passed.
- mypy passed.
- pytest passed with 38 tests and 1 warning.
- `gaia doctor` passed.
- MicroGrow read-only validation confirmed no repository mutation.

## Known Limitations

- Ollama must already be installed and configured for live model smoke tests.
- The release remains local-first and does not implement autonomous action loops.
- The conversational layer is still evidence-constrained rather than a general-purpose assistant.

## Manual Review Steps

1. Review the release notes and acceptance checklist.
2. Run `gaia doctor`.
3. Run `gaia models status`.
4. Run the acceptance questions against `gaia ask`.
5. Inspect `gaia agent runs list`.
6. Confirm MicroGrow remains unchanged before and after the review.
