# Error Model

B6 uses a structured error envelope for Project Officer API failures.

## Error payload

`ProjectOfficerApiError` contains:

- `error_code`
- `message`
- `resource_type`
- `resource_id`
- `authority_level`
- `details`

## HTTP mapping used by the API layer

- missing resources from `KeyError` map to `404`;
- blocked or state-invalid lifecycle actions map to `409`;
- the backend attaches the structured payload to `HTTPException.detail`.

## Error semantics

- `unknown_project`
- `unknown_snapshot`
- `unknown_finding`
- `unknown_recommendation`
- `unknown_work_package`
- `unknown_revision`
- `stale_package`
- `blocked_action`
- `project_revision_mismatch`
- `invalid_state_transition`

The CLI remains local and does not need the same structured envelope, but it follows the same resource boundaries and state checks.
