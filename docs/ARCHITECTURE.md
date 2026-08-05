# Architecture

## Purpose

GAIA separates deterministic evidence collection from later probabilistic AI reasoning.

```text
CLI / FastAPI
      |
ProjectService
  |       |        |
Git     Scanner   Reports
  |       |
Read-only external project
      |
SQLite catalogue, FTS index, snapshots and audit events
```

## Components

- `config.py`: loads project and runtime configuration.
- `security.py`: canonical path and filename policy.
- `git_inspector.py`: fixed read-only Git operations.
- `scanner.py`: defensive text discovery, hashing and decoding.
- `db.py`: SQLite schema, search, snapshots and audit storage.
- `service.py`: orchestrates safe workflows and integrity checks.
- `reports.py`: deterministic Markdown and JSON reports.
- `api.py`: local HTTP interface.
- `cli.py`: Windows-friendly command interface.

## Design rules

1. A model never receives arbitrary file or shell access.
2. Evidence collection works without a model.
3. Project roots and extensions are explicitly registered.
4. Scans compare Git state before and after.
5. Consequential actions remain absent in v0.1.
6. Later AI providers must call these narrow services rather than bypass them.
