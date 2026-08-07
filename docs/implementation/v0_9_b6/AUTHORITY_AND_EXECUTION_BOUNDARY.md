# Authority and Execution Boundary

B6 exposes review and lifecycle state, not execution.

## Allowed

- inspect project health, changes, recommendations, work packages, revisions, handoffs, and outcomes;
- submit a work package for review;
- approve or reject an exact revision;
- record manual handoff evidence;
- record a human-reported outcome;
- expire a package in local GAIA state.

## Not allowed

- run Codex;
- execute a generated prompt;
- execute shell commands;
- write to target repositories;
- create, commit, or push target-repository branches;
- merge target repositories;
- control hardware;
- send messages;
- download models automatically;
- use cloud fallback for execution.

## Boundary rule

The B6 API and CLI only expose the existing Project Officer planning state and the exact manual lifecycle transitions already implemented in the backend. They do not turn a review artifact into execution authority.
