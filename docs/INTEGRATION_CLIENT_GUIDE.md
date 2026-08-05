# Integration Client Guide

`packages/gaia_integration_client` is the shared Dart client for GAIA integrations.

## What It Provides

- Health checks
- Compatibility checks
- Project summaries
- Task and approval summaries
- Action summaries
- Latest brief lookup
- Receipt lookup
- Action create, request-approval, approve, execute, rollback, and cancel helpers

## When To Use It

- Use it in Flutter dashboard code.
- Use it in other Dart integrations that need the GAIA API without duplicating endpoint logic.

## Notes

- The client is intended for local and trusted integrations.
- It assumes the backend has already enforced permission and confirmation boundaries.
