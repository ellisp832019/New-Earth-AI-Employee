# GAIA v0.2 Validation

Run these checks before releasing the conversational branch:

```powershell
python -m pytest
python -m ruff check src tests
python -m mypy src\gaia
python -m compileall src
gaia doctor
gaia models status
gaia ask microgrow-v1 "Where exactly is MicroGrow currently?"
gaia agent runs list
```

## Validation expectations

- The MicroGrow repository must remain unchanged.
- Ollama may be unavailable.
- Deterministic fallback must still answer safely.
- Runtime databases and generated reports must stay untracked.
