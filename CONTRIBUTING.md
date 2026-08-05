# Contributing

## Basics

- Work on a branch.
- Keep changes focused.
- Run tests before committing.
- Do not commit runtime databases or generated evidence.

## Validation

```powershell
python -m pytest
python -m ruff check src tests
python -m mypy src\gaia
python -m compileall src
```

## Pull requests

- Open a PR against `main`.
- Include validation notes.
- Keep the branch history clean.
