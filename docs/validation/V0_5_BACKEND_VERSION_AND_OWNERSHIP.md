# GAIA v0.5 Backend Version and Ownership

## Evidence

- Stale backend observed on `127.0.0.1:8000` reported version `0.3.0` and used `data\gaia.db`.
- Fresh backend launched on `127.0.0.1:8765` reported version `0.5.0`.
- Compatibility endpoint reported `contract_version = gaia-v1` and `status = compatible`.

## Ownership Result

The v0.5 backend used for acceptance was the local, freshly launched GAIA v0.5 service, not the stale listener on port 8000.
