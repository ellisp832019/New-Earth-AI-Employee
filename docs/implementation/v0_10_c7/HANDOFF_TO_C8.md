# Handoff to C8

C7 is now complete across both repositories.

## Starting Points for C8

- GAIA main: `3a7d316f66aabf9cd677200c55fd5be05a4d6afe`
- Dashboard main: `67bb0057322ae0d5d7514bdaba5e29258ec3efda`

## What C8 Must Verify

- the full cross-repository programme intelligence contract;
- GAIA API, CLI, integration-client, and dashboard-module compatibility;
- the Dashboard exact GAIA dependency pin;
- the Dashboard read-only, fail-closed boundary;
- the Windows Control Centre programme workspace;
- v0.9 compatibility;
- migrations and data compatibility;
- release readiness;
- final version bump to `0.10.0` only after acceptance;
- final release or tag only after all gates pass.

## What C8 Must Not Introduce

- autonomous Codex execution;
- arbitrary shell execution;
- autonomous Git mutation;
- Dashboard approval or execution controls;
- direct Dashboard SQLite access;
- MicroGrow write behavior;
- cloud fallback;
- telemetry requirement;
- automatic model downloads;
- hardware-control expansion.

## Closure

- C7A: COMPLETE
- C7B: COMPLETE
- C7 cross-repository acceptance: COMPLETE
- C7 final status: READY FOR C8
