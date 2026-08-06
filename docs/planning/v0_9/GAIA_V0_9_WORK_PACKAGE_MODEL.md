# GAIA v0.9 Work Package Model

## Purpose

Work packages are human-reviewable planning units that package evidence, scope, risk, and a generated Codex prompt without executing anything.

## Required Fields

- work-package ID;
- project;
- objective;
- reason;
- evidence references;
- scope;
- non-goals;
- affected areas;
- expected files;
- security boundaries;
- risk assessment;
- backup requirements;
- implementation stages;
- validation commands;
- acceptance criteria;
- rollback plan;
- generated Codex prompt;
- approval status;
- expiry or staleness state;
- provenance manifest.

## Revision Model

- revisions should be versioned;
- each revision should preserve the prior decision trail;
- superseded packages should remain queryable;
- expired packages should not be executable.

## Packaging Rule

The package may prepare a Codex prompt, but must not run it.
