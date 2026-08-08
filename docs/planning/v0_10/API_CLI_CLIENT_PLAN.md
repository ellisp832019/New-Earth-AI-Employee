# API, CLI and Client Plan

## API Direction

Preserve the existing integration namespace and add programme-read resources in a backward-compatible way. A likely shape is:

- `/integration/v1/programme/...`
- `/integration/v1/architecture/...`
- `/integration/v1/dependencies/...`
- `/integration/v1/change-impact/...`
- `/integration/v1/release-trains/...`
- `/integration/v1/programme-packages/...`

Exact route names should follow current conventions if a narrower naming scheme is already in place.

## CLI Direction

The CLI should expose read-oriented commands such as:

- `gaia programme overview`
- `gaia architecture list`
- `gaia architecture graph`
- `gaia impact analyse`
- `gaia programme roadmap`
- `gaia release-train list`
- `gaia programme-package show`

## Integration Client Direction

Keep `packages/gaia_integration_client` as the single supported client boundary. Add typed read models and preserve v0.8 and v0.9 compatibility.
