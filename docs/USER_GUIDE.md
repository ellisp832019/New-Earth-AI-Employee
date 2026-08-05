# GAIA v0.1 User Guide

## What GAIA is today

GAIA v0.1 is the secure evidence layer for an AI employee. It reads only approved project files, captures repository state, builds a local search index and generates foundation reports.

GAIA v0.2 adds a local conversational layer that answers questions from those same evidence sources.

## Daily operation

### Check the system

```powershell
gaia doctor
```

A missing MicroGrow root is a warning. Correct `config\projects.yaml` before scanning.

### Refresh project evidence

```powershell
gaia project scan microgrow-v1
gaia project snapshot microgrow-v1
```

### Generate a report

```powershell
gaia project report microgrow-v1 --output data\reports\MICROGROW_FOUNDATION_REPORT.md
```

### Search documentation

```powershell
gaia project search microgrow-v1 "automation engine"
```

### View audit history

Start the API and open `/docs`, then execute `GET /audit/events`.

### Ask a question

```powershell
gaia ask microgrow-v1 "What was completed most recently?"
```

If Ollama is unavailable, GAIA returns a deterministic evidence-backed answer instead of pretending a model was used.

## Understanding results

- **Indexed**: approved text read successfully and added to search.
- **Skipped**: approved file identified but not indexed, usually because it exceeded the size limit.
- **Failed**: a read or processing error occurred.
- **Clean working tree**: Git reported no tracked or untracked changes.
- **Ahead/behind unknown**: the branch has no configured upstream or Git could not resolve it.

## Safety behaviour

GAIA rejects access outside a registered project, credential-like filenames, excluded directories and unapproved file extensions. A scan also compares repository state before and after and stops if it changes.

## Troubleshooting

### Python points to Espressif Python

Pass an explicit normal Python 3.11/3.12 executable to `setup_windows.ps1` when available. If the machine only has a newer compatible Python installed, point the script at that executable instead.

### FTS5 unavailable

GAIA falls back to local `LIKE` searching. Search remains functional but less capable.

### Project root missing

Edit `config\projects.yaml` and rerun `gaia doctor`.

### Scan fails because Git is unavailable

Install Git for Windows and reopen the terminal.

### API port is occupied

```powershell
gaia serve --port 8877
```
