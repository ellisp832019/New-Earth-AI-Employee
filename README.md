# New Earth AI Employee

**GAIA v0.1 — MicroGrow Project-Control Officer**

This repository is a local-first, read-only foundation for a controlled AI employee. Its first role is to inspect the external MicroGrow V1 repository, index approved text documents, capture Git state, produce deterministic evidence reports, and expose those capabilities through a CLI and FastAPI service.

GAIA v0.1 does **not** modify MicroGrow, execute unrestricted shell commands, send email, control equipment, or make autonomous changes.

GAIA v0.2 extends the foundation with a local conversational layer that answers questions from the same evidence sources while remaining read-only.

Release notes and review materials for v0.2 live under [docs/releases](docs/releases/GAIA_V0_2_0_RELEASE_NOTES.md).

## Repository relationship

```text
D:\Dev\Projects\New-Earth-AI-Employee   <- this repository
D:\Dev\Projects\MicroGrow V1           <- external read-only source
```

## Included

- strict project and path allowlisting;
- read-only Git inspection with fixed command templates;
- defensive document scanning and SHA-256 hashing;
- SQLite document catalogue and FTS5 search with fallback;
- deterministic repository snapshots and Markdown/JSON reports;
- append-only audit events;
- FastAPI endpoints;
- Typer CLI;
- Windows PowerShell setup and run scripts;
- automated tests;
- complete user, architecture, security and roadmap documentation;
- a master Codex build-and-verification prompt.

## Quick start on Windows

```powershell
cd "D:\Dev\Projects\New-Earth-AI-Employee"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
gaia doctor
gaia project scan microgrow-v1
gaia project snapshot microgrow-v1
gaia project report microgrow-v1 --format markdown --output ".\data\reports\microgrow-foundation.md"
gaia ask microgrow-v1 "Where exactly is MicroGrow currently?"
```

Start the API:

```powershell
.\scripts\start_api.ps1
```

Then open `http://127.0.0.1:8765/docs`.

## Safety boundary

All file access is checked against the configured project root, approved extensions, excluded directories, secret-bearing filenames, and canonical resolved paths. Git access uses `subprocess` without `shell=True` and only fixed read-only commands.

Read [docs/START_HERE.md](docs/START_HERE.md) first.
