# Architecture Acceptance

## Canonical Authority

- Python/FastAPI remains the canonical GAIA source of truth.
- The Windows Control Centre remains the trusted engineering workspace.
- Flutter remains a read-only/read-mostly consumer surface.
- The Dashboard does not read GAIA SQLite directly.

## No Duplicate Engines

- no second architecture registry;
- no duplicate dependency graph;
- no duplicate change-impact engine;
- no duplicate programme-package engine;
- no competing persistence layer.

## Release Surface

The release retains the supported split:

- backend and canonical logic in GAIA;
- reusable client and dashboard-module surfaces for external consumption;
- Dashboard UI for read-only programme intelligence;
- no migration of programme-intelligence business logic into Flutter.
