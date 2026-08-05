# User Guide

GAIA v0.5 keeps the same local-first workflow, but adds a controlled way to write output.

## Typical Flow

1. Inspect the project or task.
1. Create a permission manifest for the intended output root and action types.
1. Create an output action and review its exact preview.
1. Request approval, then approve it.
1. Execute the action only when you are ready.
1. Review the receipt and rollback record if needed.

## What Changed In v0.5

- Output writes are no longer implicit.
- Every write has a manifest, action, approval, receipt, and optional backup.
- The Windows control centre now has dedicated Permissions, Action Centre, and Receipts screens.

## MicroGrow Safety

MicroGrow stays read-only. GAIA can inspect it, summarize it, and export from it, but it should not modify the external repository.
