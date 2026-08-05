from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator


class OllamaProviderConfig(BaseModel):
    enabled: bool = False
    base_url: HttpUrl | str = "http://127.0.0.1:11434"
    model: str = ""
    request_timeout_seconds: float = 30.0
    connection_timeout_seconds: float = 5.0
    max_response_bytes: int = 200_000
    max_context_chars: int = 12_000
    max_retries: int = 0

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: HttpUrl | str) -> str:
        return str(value)


class ModelRoutingSettings(BaseModel):
    enabled: bool = False
    default_provider: Literal["mock", "ollama", "none"] = "mock"
    providers: dict[str, OllamaProviderConfig] = Field(default_factory=dict)


def load_model_routing(path: str | Path | None = None) -> ModelRoutingSettings:
    resolved = Path(path or "config/model-routing.yaml")
    if not resolved.exists():
        return ModelRoutingSettings()
    raw = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Model routing configuration must be a mapping")
    providers: dict[str, OllamaProviderConfig] = {}
    provider_map = raw.get("providers", {})
    if not isinstance(provider_map, dict):
        raise ValueError("'providers' must be a mapping")
    for name, value in provider_map.items():
        if not isinstance(value, dict):
            raise ValueError(f"Provider '{name}' must be a mapping")
        try:
            providers[name] = OllamaProviderConfig(**value)
        except ValidationError as exc:
            raise ValueError(f"Invalid provider '{name}'") from exc
    enabled = bool(raw.get("enabled", False))
    default_provider = raw.get("default_provider", "mock")
    if default_provider not in {"mock", "ollama", "none"}:
        raise ValueError("default_provider must be mock, ollama or none")
    return ModelRoutingSettings(
        enabled=enabled,
        default_provider=default_provider,
        providers=providers,
    )
