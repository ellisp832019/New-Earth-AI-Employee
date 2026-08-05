# Agent Runs

GAIA records conversational runs locally.

## Stored fields

- Run ID
- Project ID
- User question
- Question category
- Snapshot ID
- Search queries
- Selected evidence
- Provider and model
- Start and finish timestamps
- Status
- Structured answer
- Confidence
- Warnings

## Commands

```powershell
gaia agent runs list
gaia agent runs show <run-id>
```

## Privacy

- Do not commit the runtime agent-run database.
- Do not push private questions or answers to GitHub.
