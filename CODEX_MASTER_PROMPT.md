# Codex Master Prompt — Build, Verify and Continue GAIA v0.1

Copy everything below into Codex while the extracted repository is open in VS Code.

---

You are the lead software architect, security reviewer, test engineer and documentation maintainer for:

NEW EARTH AI EMPLOYEE

Employee identity:

GAIA — New Earth Operations Coordinator

Initial operational role:

MicroGrow Project-Control Officer

## Repository paths

Primary repository:

D:\Dev\Projects\New-Earth-AI-Employee

External inspected repository:

D:\Dev\Projects\MicroGrow V1

The external MicroGrow repository is strictly read-only for this work. Do not modify its files, Git index, branch, configuration, working tree or history.

## Package context

This repository was supplied as a complete GAIA v0.1 foundation package. It should already contain:

- Python package under `src/gaia`;
- FastAPI application;
- Typer CLI;
- project registry;
- path-security controls;
- fixed read-only Git inspector;
- document scanner and index;
- SQLite FTS5 search with fallback;
- snapshots and reports;
- audit records;
- Windows scripts;
- automated tests;
- architecture, security, user and operations documentation.

Your task is to inspect, run, verify, repair and complete the package—not to blindly replace it.

## Primary objective

Deliver a fully working, tested and documented GAIA v0.1 read-only evidence foundation on Windows, prove that it does not modify MicroGrow, and create one intentional commit.

Do not add model integration, autonomous behaviour, arbitrary shell access, write tools, Flutter, email, calendar, financial functions or physical-device control in this work package.

## Mandatory workflow

### 1. Preflight

- Confirm the current repository root.
- Inspect all existing files before changing anything.
- Run `git status`, current branch and current commit checks.
- Create a suitable implementation branch if the repository has no branch dedicated to this package.
- Review `README.md`, `docs/START_HERE.md`, `docs/SECURITY_MODEL.md`, `docs/USER_GUIDE.md`, `docs/GAIA_V0_1_ROADMAP.md` and this prompt.
- Confirm the configured MicroGrow path.
- Capture MicroGrow branch, commit and porcelain status before any GAIA operation.
- Record the preflight evidence in `docs/validation/PREFLIGHT.md`.

### 2. Environment setup

- Use Python 3.11 or 3.12.
- Do not assume the `py` launcher exists.
- Run or repair `scripts/setup_windows.ps1`.
- Install editable development dependencies.
- Run `gaia doctor`.
- Confirm Git is available.
- Confirm SQLite starts and whether FTS5 is available.

### 3. Full code review

Review every implementation module for:

- correctness;
- Windows path semantics;
- fail-closed security;
- type correctness;
- subprocess safety;
- database transactions;
- API error handling;
- audit completeness;
- secret leakage;
- deterministic reports;
- read-only integrity.

Pay special attention to:

- path traversal using `..`;
- absolute paths outside the project root;
- mixed separators;
- Windows case-insensitive comparisons;
- symlinks and junctions;
- excluded directories;
- secret-bearing names;
- malformed text encodings;
- large files;
- unavailable upstream branches;
- credential-bearing remote URLs;
- Git timeouts;
- truncated command output;
- FTS5 query syntax errors;
- repeated scans;
- database cleanup and connection lifetime;
- API startup in tests;
- command exit codes.

Repair defects with the smallest clear changes. Do not weaken protections to make tests pass.

### 4. Complete test coverage

Run the existing suite and add tests where coverage is insufficient.

Mandatory test categories:

- configuration;
- registry validation;
- normal approved paths;
- relative traversal;
- absolute external paths;
- mixed Windows separators;
- case differences;
- nested traversal;
- symlink or junction escape where testable;
- disallowed extensions;
- excluded directories;
- environment and credential filenames;
- secret-name detection;
- binary/invalid text;
- oversized files;
- SHA-256 stability;
- Git root, branch, SHA and status;
- untracked and changed files;
- remote redaction;
- subprocess without `shell=True`;
- timeout and output-size handling;
- database replacement;
- FTS5 and fallback search;
- snapshots;
- deterministic Markdown/JSON reports;
- audit events;
- all API routes;
- CLI commands;
- full inspection workflow;
- proof that a scan does not modify the inspected repository.

Run formatting, linting, type checking and tests. Document exact results.

### 5. Real MicroGrow validation

Against `D:\Dev\Projects\MicroGrow V1`:

- run `gaia doctor`;
- run the project scan;
- create a snapshot;
- generate Markdown and JSON foundation reports;
- perform searches for:
  - `PlatformIO build verification`;
  - `release readiness`;
  - `experimental`;
  - `future version`;
  - `user guide`;
- inspect audit events;
- confirm no source document contents or secrets appear in audit metadata;
- capture MicroGrow branch, commit and porcelain status again;
- compare them with preflight evidence;
- fail the work package if GAIA changed MicroGrow.

Store generated validation evidence under:

- `docs/validation/VALIDATION_REPORT.md`
- `docs/validation/MICROGROW_READ_ONLY_PROOF.md`
- `docs/validation/TEST_RESULTS.md`

Generated operational reports may remain under ignored `data/reports/` and should not be committed unless sanitised and intentionally approved.

### 6. Documentation review

Ensure all documentation is accurate and usable by Peter on Windows.

Mandatory documents:

- README.md
- docs/START_HERE.md
- docs/ARCHITECTURE.md
- docs/SECURITY_MODEL.md
- docs/DATA_MODEL.md
- docs/PROJECT_REGISTRY.md
- docs/CLI_REFERENCE.md
- docs/API_REFERENCE.md
- docs/TESTING.md
- docs/WINDOWS_SETUP.md
- docs/MICROGROW_INSPECTION_GUIDE.md
- docs/USER_GUIDE.md
- docs/OPERATIONS_RUNBOOK.md
- docs/EMPLOYEE_HANDBOOK.md
- docs/GAIA_V0_1_ROADMAP.md

Correct commands and paths. Explain limitations honestly.

### 7. Security review

Verify that:

- no unrestricted terminal function exists;
- all Git operations are fixed and read-only;
- no `shell=True` exists;
- project content cannot alter GAIA policy;
- no write tool exists for the external project;
- path resolution fails closed;
- secrets are excluded;
- audit events avoid content and credentials;
- the API binds locally by default;
- no credentials are committed;
- `.env.example` contains placeholders only.

Run a secret scan or equivalent inspection over the GAIA repository before commit.

### 8. Final Git and commit workflow

- Review the entire diff.
- Remove caches, generated databases, reports and temporary files.
- Confirm the GAIA working tree contains only intentional changes.
- Confirm the MicroGrow working tree and commit remain exactly as captured before validation.
- Commit with:

`feat(gaia): validate read-only project inspection foundation`

Do not push unless explicitly instructed.

## Completion requirements

Do not claim completion unless all applicable checks pass.

Your final report must include:

- GAIA repository path;
- branch;
- commit SHA;
- Python version;
- architecture summary;
- modules reviewed and changed;
- all CLI commands;
- all API endpoints;
- database and FTS5 status;
- test count and pass/fail result;
- lint and type-check results;
- pre-scan MicroGrow branch, SHA and status;
- post-scan MicroGrow branch, SHA and status;
- explicit read-only proof;
- snapshot ID;
- generated report paths;
- search validation results;
- security-review result;
- limitations and warnings;
- exact commands Peter should run next.

## Non-negotiable boundaries

- Never modify MicroGrow.
- Never run Git mutation commands against MicroGrow.
- Never add arbitrary shell execution.
- Never add model-provider integration during this package.
- Never add write or delete tools.
- Never add email, calendar, financial or physical-control integrations.
- Never hide failed tests.
- Never weaken security to achieve a passing result.
- Never push without explicit instruction.

Begin by inspecting the repository and producing the preflight evidence. Continue through the entire scoped workflow without waiting for routine confirmation. Stop only if a genuine safety boundary prevents progress, and report the exact blocker with evidence.

---
