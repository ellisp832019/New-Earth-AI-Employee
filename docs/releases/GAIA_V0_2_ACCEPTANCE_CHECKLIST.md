# GAIA v0.2 Acceptance Checklist

Use this checklist to approve GAIA v0.2.0 for release review.

## Repository and Safety

- [ ] Working tree is clean.
- [ ] Branch is `gaia-v0.2-local-conversational-agent`.
- [ ] Remote branch is current on `origin`.
- [ ] MicroGrow is still read-only.
- [ ] No runtime databases, logs, caches, or generated reports are tracked.
- [ ] No cloud AI dependency is required.

## Core Commands

- [ ] `gaia doctor`
- [ ] `gaia models status`
- [ ] `gaia models list`
- [ ] `gaia ask microgrow-v1 "Where exactly is MicroGrow currently?"`
- [ ] `gaia ask microgrow-v1 "What should I build next?"`
- [ ] `gaia ask microgrow-v1 "Create the next Codex prompt"`
- [ ] `gaia agent runs list`
- [ ] `gaia agent runs show <run-id>`
- [ ] `gaia project scan microgrow-v1`
- [ ] `gaia project snapshot microgrow-v1`
- [ ] `gaia project search microgrow-v1 "PlatformIO build verification"`

## Security Checks

- [ ] Prompt-injection warnings are surfaced.
- [ ] Deterministic fallback works when Ollama is unavailable.
- [ ] Ollama remains loopback-only.
- [ ] No command execution or external project write capability exists.
- [ ] Evidence remains traceable.
- [ ] Absolute host paths are not exposed unnecessarily.

## Quality Gates

- [ ] `python -m compileall src tests`
- [ ] `python -m ruff check src tests`
- [ ] `python -m mypy src\gaia`
- [ ] `python -m pytest`

## Documentation

- [ ] Release notes exist.
- [ ] PR summary exists.
- [ ] Known limitations exist.
- [ ] v0.3 handoff exists.
- [ ] Validation evidence exists.

## Approval Rule

Only approve the release when every required command passes and every safety check is satisfied with evidence.
