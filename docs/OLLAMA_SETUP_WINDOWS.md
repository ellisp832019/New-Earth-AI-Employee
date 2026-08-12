# Legacy Ollama Notes

GAIA no longer uses Ollama as its canonical execution boundary.

If the Local AI Runtime is configured to route to an Ollama backend, follow the Local AI Runtime repository documentation and the Runtime configuration file in this repository. GAIA itself should only be pointed at the Runtime loopback endpoint.

## What to do instead

- Configure `config\model-routing.yaml` for the Local AI Runtime boundary.
- Verify `gaia doctor` and `gaia models status`.
- Do not add direct `ollama` execution calls to GAIA code.

## Historical reference

Older GAIA notes referred to direct Ollama setup. Those notes are retained only for historical context and should not be treated as the current GAIA execution model.
