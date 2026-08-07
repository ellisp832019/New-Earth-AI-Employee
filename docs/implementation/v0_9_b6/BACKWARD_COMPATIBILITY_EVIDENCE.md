# Backward Compatibility Evidence

B6 was implemented without breaking the v0.8 consumer path.

## Evidence in the merged code

- `packages/gaia_integration_client` kept its existing v0.8 methods.
- `packages/gaia_dashboard_module` continued to consume the official integration client.
- `apps/gaia_windows` continued to use the same integration-client path for B5 workspace flows.
- `pyproject.toml` and `packages/gaia_integration_client/pubspec.yaml` remained at version `0.8.0`.
- the older `/integration/v1/compatibility` route remains available.

## PR and CI evidence

- PR: `#16`
- B6 head: `c99c67ca8e495db8ae26b0267a3095a5615acdf4`
- merge commit: `797735b55fd2ad34e3283706b09c69997b75610f`
- GitHub Actions completed successfully for:
  - `python (3.11)`
  - `python (3.14)`
  - `dart_integration_client`
  - `dashboard_module`
  - `example_host`
  - `windows_app`
  - `windows_validation`

## Compatibility summary

B6 adds a new versioned Project Officer surface instead of changing the old one. That keeps v0.8 consumers working while providing a clearer contract for B7 and later work.
