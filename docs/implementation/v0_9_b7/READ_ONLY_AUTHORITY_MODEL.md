# Read-Only Authority Model

The dashboard module is an observer, not an executor.

## Allowed

- fetch integration-client data
- render summary cards and lists
- label stale, unavailable, incompatible, partial, and empty states
- display read-only evidence and alerts

## Not allowed

- approve or reject work packages
- submit work packages for review
- hand off packages
- record outcomes
- execute actions
- modify repositories
- access SQLite directly
- manage retention or signing

## Proof intent

The dashboard code path does not call lifecycle mutation operations and the UI does not expose controls for them.
