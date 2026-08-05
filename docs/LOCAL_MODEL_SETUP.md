# Local Model Setup

GAIA v0.2 supports local model routing through Ollama, but it remains usable when no model is configured.

## Default behavior

- Provider routing is disabled by default.
- The mock provider is available for deterministic testing.
- Ollama is only used when explicitly enabled.

## Configure Ollama

Edit `config\model-routing.yaml` and set:

- `enabled: true`
- `providers.ollama.enabled: true`
- `providers.ollama.model: <your-model-name>`

## Check status

```powershell
gaia doctor
gaia models status
```

## Limits

- Ollama is expected to run on loopback by default.
- GAIA will fall back to deterministic answers if Ollama is unavailable.
