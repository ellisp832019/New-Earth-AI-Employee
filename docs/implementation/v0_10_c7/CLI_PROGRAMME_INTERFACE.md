# CLI Programme Interface

## Purpose

Provide read-only programme commands that mirror the public API and canonical Python services.

## Added Commands

- `gaia programme overview`
- `gaia programme summary`
- `gaia programme roadmap`
- `gaia architecture list`
- `gaia architecture relationships`
- `gaia architecture graph`
- `gaia impact analyse`
- `gaia impact recommendations`
- `gaia release-train list`
- `gaia release-train show`
- `gaia programme-package list`
- `gaia programme-package show`

## Constraint

The CLI must remain read-only and must not approve, reject, hand off, execute, or mutate any repository state.
