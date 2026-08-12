# Local AI Runtime Setup

GAIA now consumes the canonical New Earth Local AI Runtime for model execution. GAIA remains read-only and evidence-driven; the Runtime owns provider routing, generation, embeddings and route provenance.

## Default behavior

- The Local AI Runtime integration is enabled by default.
- The deterministic fallback remains available when the Runtime is unavailable or incompatible.
- GAIA never talks to provider HTTP endpoints directly in production code.

## Configure the Runtime boundary

Edit `config\model-routing.yaml` and adjust:

- `local_ai_runtime.enabled: true`
- `local_ai_runtime.base_url: http://127.0.0.1:8787`
- `local_ai_runtime.api_version: v1`
- `local_ai_runtime.require_local_only: true`

## Check status

```powershell
gaia doctor
gaia models status
```

## Limits

- The Runtime is expected to stay on loopback by default.
- GAIA falls back to deterministic answers if the Runtime is unavailable, degraded or incompatible.
- GAIA does not automatically download models.
