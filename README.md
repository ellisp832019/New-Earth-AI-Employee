# New Earth AI Employee

**GAIA v0.6.0 - Dashboard integration and trust layer**

This repository is a local-first, read-only foundation for a controlled AI employee. Its first role is to inspect the external MicroGrow V1 repository, index approved text documents, capture Git state, produce deterministic evidence reports, and expose those capabilities through a CLI, FastAPI service, and a Windows desktop control centre.

GAIA v0.1 does **not** modify MicroGrow, execute unrestricted shell commands, send email, control equipment, or make autonomous changes.

GAIA v0.2 extends the foundation with a local conversational layer that answers questions from the same evidence sources while remaining read-only.

GAIA v0.3 adds a Flutter-based Windows desktop shell that connects to the existing read-only backend, keeps MicroGrow read-only, and surfaces evidence, reports, snapshots, agent runs, and audit history.

GAIA v0.4 adds controlled task records, draft records, approval records, a deterministic daily operations brief, and the corresponding CLI, API, desktop and VS Code operator workflows. Approvals remain manual-use decisions only and do not execute actions.

GAIA v0.5 adds permission manifests, GAIA-owned output workspace enforcement, exact write previews, explicit user-triggered execution, execution receipts, backup and rollback records, a reusable integration client, and the GAIA v1 OpenAPI compatibility contract.

GAIA v0.5.1 is a focused hotfix for managed backend ownership checks, safe start/stop behavior, stale PID-file handling, and UTF-8-safe Windows status output.

GAIA v0.6.0 adds the reusable dashboard module, example dashboard host, stronger compatibility and degraded-mode reporting, tamper-evident receipt chains, offline review packages, versioned action templates, retention policy scaffolding, and Trust Centre/integration screens.

Release notes and review materials for v0.2 live under [docs/releases](docs/releases/GAIA_V0_2_0_RELEASE_NOTES.md).
Release notes for v0.3 live under [docs/releases](docs/releases/GAIA_V0_3_0_RELEASE_NOTES.md).
Release notes for v0.4 live under [docs/releases](docs/releases/GAIA_V0_4_0_RELEASE_NOTES.md).
Release notes for v0.5 live under [docs/releases](docs/releases/GAIA_V0_5_0_RELEASE_NOTES.md).
Release notes for v0.5.1 live under [docs/releases](docs/releases/GAIA_V0_5_1_RELEASE_NOTES.md).
Release notes for v0.6.0 live under [docs/releases](docs/releases/GAIA_V0_6_0_RELEASE_NOTES.md).

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
- Flutter Windows desktop control centre;
- Windows PowerShell setup and run scripts;
- automated tests;
- complete user, architecture, security and roadmap documentation;
- a master Codex build-and-verification prompt.

## Quick start on Windows

```powershell
cd "D:\Dev\Projects\New-Earth-AI-Employee"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
.\scripts\setup_flutter_windows.ps1
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

Start the Windows control centre:

```powershell
.\scripts\run_gaia_windows.ps1
```

The desktop client connects to the local GAIA backend on `http://127.0.0.1:8000`.

## Safety boundary

All file access is checked against the configured project root, approved extensions, excluded directories, secret-bearing filenames, and canonical resolved paths. Git access uses `subprocess` without `shell=True` and only fixed read-only commands.

Read [docs/START_HERE.md](docs/START_HERE.md) first.
