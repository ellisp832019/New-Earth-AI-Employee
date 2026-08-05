# Ollama Setup on Windows

## Install Ollama

- Download Ollama from the official Ollama site.
- Install it normally on Windows.
- Start the Ollama service.

## Pull a model

```powershell
ollama pull llama3.1
```

## Configure GAIA

Set `config\model-routing.yaml` so Ollama uses the model name you pulled.

## Verify

```powershell
gaia doctor
gaia models status
```

## Troubleshooting

- If Ollama is not running, GAIA will use deterministic fallback behavior.
- If the model is missing, configure the model name correctly or pull the model again.
