# Security and Read-Only Boundary

## Security Boundary

- no arbitrary command execution;
- no Codex execution;
- no autonomous Git operations;
- no external repository mutation;
- no release publication;
- no deployment automation.

## Read-Only Rule

The public programme API, CLI, integration client, and dashboard module consume canonical GAIA services only and do not mutate the workspace.
