from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx

from gaia.conversation import ModelRequest, ModelResponse, ModelStatus
from gaia.routing import ModelRoutingSettings, OllamaProviderConfig


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...

    async def status(self) -> ModelStatus: ...


class MockModelProvider:
    def __init__(self, model_name: str = "mock-gaia") -> None:
        self.model_name = model_name

    async def generate(self, request: ModelRequest) -> ModelResponse:
        evidence_lines = "\n".join(
            f"- {item.source_path}: {item.snippet[:160]}" for item in request.evidence[:8]
        ) or "- No evidence selected"
        content = (
            "Facts:\n"
            f"{evidence_lines}\n\n"
            "Inference:\n"
            "This response is produced deterministically from local evidence.\n\n"
            "Recommendation:\n"
            "Use the evidence above and, if needed, request a fresh snapshot before making changes."
        )
        return ModelResponse(
            provider="mock",
            model_name=self.model_name,
            endpoint_identity="local-mock",
            content=content,
            usage={"prompt_chars": len(request.system_prompt) + len(request.user_question)},
            warnings=[],
            available=True,
        )

    async def status(self) -> ModelStatus:
        return ModelStatus(provider="mock", available=True, model_name=self.model_name, endpoint_identity="local-mock", details="Deterministic local provider")


class OllamaModelProvider:
    def __init__(self, config: OllamaProviderConfig) -> None:
        self.config = config
        parsed = urlparse(str(config.base_url))
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Ollama endpoint must default to loopback-only access")
        self.base_url = str(config.base_url).rstrip("/")
        self.model_name = config.model

    async def status(self) -> ModelStatus:
        if not self.config.enabled:
            return ModelStatus(
                provider="ollama",
                available=False,
                model_name=self.config.model or None,
                endpoint_identity=self.base_url,
                details="Ollama integration disabled",
            )
        try:
            async with httpx.AsyncClient(timeout=self.config.connection_timeout_seconds) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return ModelStatus(
                provider="ollama",
                available=False,
                model_name=self.config.model or None,
                endpoint_identity=self.base_url,
                details=f"Unavailable: {type(exc).__name__}",
            )
        models = payload.get("models", []) if isinstance(payload, dict) else []
        if self.config.model and not any(model.get("name") == self.config.model for model in models if isinstance(model, dict)):
            return ModelStatus(
                provider="ollama",
                available=False,
                model_name=self.config.model,
                endpoint_identity=self.base_url,
                details="Configured model not found",
            )
        return ModelStatus(
            provider="ollama",
            available=True,
            model_name=self.config.model or None,
            endpoint_identity=self.base_url,
            details="Ollama reachable",
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if not self.config.enabled:
            return ModelResponse(
                provider="ollama",
                model_name=self.config.model or None,
                endpoint_identity=self.base_url,
                content="",
                available=False,
                error="Ollama integration disabled",
            )
        prompt = f"{request.system_prompt}\n\n{request.endpoint_identity}\n\n{request.user_question}\n\n{request.analysis.category}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.config.request_timeout_seconds)) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt[: self.config.max_context_chars],
                        "stream": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            return ModelResponse(
                provider="ollama",
                model_name=self.config.model or None,
                endpoint_identity=self.base_url,
                content="",
                available=False,
                error=f"Timeout: {type(exc).__name__}",
            )
        except Exception as exc:
            return ModelResponse(
                provider="ollama",
                model_name=self.config.model or None,
                endpoint_identity=self.base_url,
                content="",
                available=False,
                error=type(exc).__name__,
            )
        content = str(payload.get("response", "")) if isinstance(payload, dict) else ""
        if len(content.encode("utf-8")) > self.config.max_response_bytes:
            content = content.encode("utf-8")[: self.config.max_response_bytes].decode("utf-8", errors="ignore")
        return ModelResponse(
            provider="ollama",
            model_name=self.config.model or None,
            endpoint_identity=self.base_url,
            content=content,
            usage=payload.get("prompt_eval_count", {}) if isinstance(payload, dict) else {},
            available=True,
            warnings=[],
        )


@dataclass(slots=True)
class ProviderSelection:
    name: str
    provider: ModelProvider
    model_name: str | None


class ProviderRegistry:
    def __init__(self, routing: ModelRoutingSettings) -> None:
        self.routing = routing
        self.mock = MockModelProvider()
        self.ollama = OllamaModelProvider(routing.providers.get("ollama", OllamaProviderConfig()))

    def select(self, provider_name: str | None = None) -> ProviderSelection:
        name = provider_name or self.routing.default_provider
        if name == "ollama":
            return ProviderSelection("ollama", self.ollama, self.ollama.model_name or None)
        return ProviderSelection("mock", self.mock, self.mock.model_name)

    async def list_status(self) -> list[ModelStatus]:
        return [await self.mock.status(), await self.ollama.status()]
