from __future__ import annotations

from pathlib import Path

from gaia.local_ai_runtime import LocalAIRuntimeSettings, load_local_ai_runtime

ModelRoutingSettings = LocalAIRuntimeSettings
OllamaProviderConfig = LocalAIRuntimeSettings


def load_model_routing(path: str | Path | None = None) -> LocalAIRuntimeSettings:
    return load_local_ai_runtime(path)
