# Conversational Agent

GAIA v0.2 adds read-only evidence-backed question answering.

## What it can do

- Answer questions using current Git facts, snapshots and indexed documents.
- Track a conversational run locally.
- Distinguish deterministic fallback answers from provider-backed answers.
- Draft a Codex prompt without executing it.

## What it cannot do

- Modify MicroGrow.
- Run arbitrary shell commands.
- Send email or control external devices.
- Execute generated Codex prompts.

## Main commands

```powershell
gaia ask microgrow-v1 "Where exactly is MicroGrow currently?"
gaia ask microgrow-v1 "What was completed most recently?"
gaia agent runs list
gaia agent runs show <run-id>
```
