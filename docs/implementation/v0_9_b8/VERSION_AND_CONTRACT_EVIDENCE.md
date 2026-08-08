# Version and Contract Evidence

## Live Release Metadata

- `VERSION`: `0.9.0`
- `pyproject.toml`: `0.9.0`
- `src/gaia/__init__.py`: `0.9.0`
- `apps/gaia_windows/pubspec.yaml`: `0.9.0+1`
- `packages/gaia_integration_client/pubspec.yaml`: `0.9.0`
- `packages/gaia_dashboard_module/pubspec.yaml`: `0.9.0`
- `examples/gaia_dashboard_host/pubspec.yaml`: `0.9.0`

## Contract Evidence

- `contracts/openapi/gaia-v1.json` regenerates from the live backend and now reports backend version `0.9.0`.
- The Project Officer API already exposes versioned capability discovery at `api_version = 0.9.0`, `contract_version = gaia-v3`, and `capability_version = 0.9.0`.
- The Dashboard integration surface map now reflects the release-controlled `0.9.0` package versions.

## Historical References Preserved

- v0.8 release notes and evidence remain at `0.8.0`.
- B6 compatibility evidence remains historical and is not rewritten.
- planning documents continue to describe the v0.9 design baseline against the earlier v0.8 release.

