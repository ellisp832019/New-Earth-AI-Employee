# Dashboard Integration Contract

The future New Earth Dashboard must talk to GAIA through the public API and the reusable dashboard module.

## Contract points

- loopback-first connection by default;
- explicit compatibility reporting;
- capability-gated UI features;
- read-mostly embedded dashboard behavior;
- dedicated execution remains in the Windows Control Centre or CLI.

## Bans

- no direct SQLite access;
- no duplicate permission logic;
- no bypass of GAIA-owned output controls;
- no silent execution through the embedded dashboard.
