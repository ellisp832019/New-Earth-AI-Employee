# Risk, Backup and Rollback Model

B4 records a conservative execution envelope.

## Risk model

- risk is derived from recommendation priority, evidence freshness, blockers, findings, and project access mode;
- high and critical risk packages must explain why the package is risky;
- blocked source recommendations remain visible as blocked packages.

## Backup model

- capture the baseline repository state before implementation;
- keep the current working tree state if the project is not clean;
- refresh project-health evidence before approval if needed.

## Rollback model

- return to the recorded baseline commit or the last approved revision;
- abandon newer revisions if evidence or scope changes materially;
- use repository-native rollback steps only in the permitted environment.
