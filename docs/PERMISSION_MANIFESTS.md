# Permission Manifests

Permission manifests are the gatekeeper for every output-writing action in GAIA v0.5.

## Purpose

- Define what action types a workflow may use.
- Bind actions to an allowlisted GAIA-owned output root.
- Cap risk, size, overwrite behavior, backup requirements, and rollback requirements.
- Keep execution explicit instead of automatic.

## Key Fields

- `allowed_action_types`
- `allowed_root`
- `maximum_file_size`
- `risk_ceiling`
- `overwrite_policy`
- `backup_requirement`
- `rollback_requirement`
- `enabled`

## Manifest Lifecycle

1. Create a manifest.
1. Validate it for missing or unsafe configuration.
1. Review it and enable or disable it.
1. Use it as the policy binding for output actions.

## Safety Rules

- Target paths are normalized and checked against the manifest root.
- Traversal, hidden `.git` paths, reserved Windows names, ADS paths, and UNC/device-style paths are rejected.
- A disabled or version-changed manifest invalidates dependent approvals.

## Live Proof

The v0.5 acceptance run created manifest `cca73a4d-601d-430a-bc2f-762debc9b1f9`, reviewed it to version 2, and used it to permit create and update output actions in the GAIA-owned workspace.
