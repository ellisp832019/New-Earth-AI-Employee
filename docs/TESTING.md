# Testing

Run:

```powershell
.\scripts\run_tests.ps1
```

The suite covers:

- configuration loading;
- path allowlisting and traversal rejection;
- excluded names and extensions;
- Git state inspection;
- read-only integrity;
- document scanning and oversized files;
- SQLite indexing and search;
- audit persistence;
- complete scan/snapshot/report workflow;
- API health, projects, scanning, search and reporting.

Tests use temporary Git repositories and never touch the real MicroGrow repository.
