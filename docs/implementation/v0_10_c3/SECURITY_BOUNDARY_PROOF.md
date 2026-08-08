# Security Boundary Proof

## Allowed

- read canonical local repository state;
- build deterministic analysis models;
- read work-package records;
- return typed impact evidence.

## Not Allowed

- running generated prompts;
- invoking Codex automatically;
- executing arbitrary shell commands;
- executing declared validation commands automatically;
- writing external repositories;
- changing branches;
- committing;
- pushing;
- merging;
- downloading models;
- controlling hardware;
- sending messages.

## Proof Point

`ChangeImpactService` is a pure analysis service. It derives a result from canonical records and returns it without performing side effects outside the local read path.
