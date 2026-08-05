# Codex Prompt Drafting

GAIA v0.2 can draft a next-step Codex prompt from evidence.

## Output rule

- The draft is always labeled `DRAFT - NOT EXECUTED`.
- GAIA never executes the prompt.

## Inputs

- Repository path
- Branch
- Commit SHA
- Working-tree state
- Snapshot ID
- Relevant evidence
- Objective
- Exclusions

## Use case

Use this when you want a safe, evidence-based prompt for the next work package.
