from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SERVICE_NAME = "new-earth-local-ai-runtime"
API_VERSION = "v1"


def _is_loopback_host(hostname: str | None) -> bool:
    return hostname in {"127.0.0.1", "localhost", "::1"}


class LocalAIRuntimeSettings(BaseModel):
    enabled: bool = True
    base_url: HttpUrl | str = "http://127.0.0.1:8787"
    api_version: str = API_VERSION
    request_timeout_seconds: float = 30.0
    connection_timeout_seconds: float = 5.0
    require_local_only: bool = True

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: HttpUrl | str) -> str:
        resolved = str(value).rstrip("/")
        parsed = urlparse(resolved)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Local AI Runtime base URL must use http or https")
        if parsed.scheme == "https" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Local AI Runtime must default to loopback-only access")
        return resolved

    @field_validator("api_version")
    @classmethod
    def _validate_api_version(cls, value: str) -> str:
        cleaned = value.strip().lstrip("/")
        if not cleaned:
            raise ValueError("api_version must not be empty")
        return cleaned


class RuntimeErrorBase(RuntimeError):
    pass


class LocalAIRuntimeUnavailable(RuntimeErrorBase):
    pass


class LocalAIRuntimeSchemaError(RuntimeErrorBase):
    pass


class LocalAIRuntimeHTTPError(RuntimeErrorBase):
    pass


class VersionedModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schema_version: Literal["v1"] = "v1"


class RuntimeResourceSnapshot(VersionedModel):
    os_name: str
    os_version: str | None = None
    cpu_count: int | None = None
    memory_total_gb: float | None = None
    memory_available_gb: float | None = None
    gpu_available: bool | None = None
    vram_total_gb: float | None = None
    disk_free_gb: float | None = None
    ollama_available: bool | None = None
    notes: list[str] = Field(default_factory=list)


class RuntimeDecision(VersionedModel):
    requested_task: str
    requested_model: str | None = None
    selected_model: str
    selected_provider: str
    provider_model_name: str
    reason: str
    fallback_used: bool = False
    resource_constraints: dict[str, Any] = Field(default_factory=dict)
    resource_snapshot: RuntimeResourceSnapshot | None = None


class RuntimeRouteExplainResponse(VersionedModel):
    decision: RuntimeDecision


class RuntimeModelRecord(VersionedModel):
    id: str
    display_name: str
    provider: str
    provider_model_name: str
    purpose: str = "general"
    task_types: list[str] = Field(default_factory=list)
    enabled: bool = True
    preferred: bool = False
    context_window: int | None = None
    approximate_ram_requirement: int | None = None
    approximate_vram_requirement: int | None = None
    embedding_model: bool = False
    code_model: bool = False
    reasoning_model: bool = False
    conversational_model: bool = False
    privacy_class: str = "local"
    notes: str = ""
    tags: list[str] = Field(default_factory=list)
    priority: int = 0


class RuntimeModelListResponse(VersionedModel):
    service: str = SERVICE_NAME
    version: str
    models: list[RuntimeModelRecord] = Field(default_factory=list)


class RuntimeCapability(VersionedModel):
    service: str = SERVICE_NAME
    version: str
    local_only: bool
    capabilities: list[str] = Field(default_factory=list)
    api_base: str | None = None
    providers: list[str] = Field(default_factory=list)
    selected_default_model: str | None = None


class RuntimeHealthResponse(VersionedModel):
    status: Literal["ok", "degraded", "warn", "fail"]
    service: str = SERVICE_NAME
    version: str
    local_only: bool
    providers: dict[str, bool] = Field(default_factory=dict)
    runtime: RuntimeCapability | None = None
    resources: RuntimeResourceSnapshot | None = None


class RuntimeStatusResponse(VersionedModel):
    service: str = SERVICE_NAME
    version: str
    local_only: bool
    host: str
    port: int
    api_base: str
    selected_default_model: str | None = None
    selected_embedding_model: str | None = None
    providers: dict[str, bool] = Field(default_factory=dict)
    resources: RuntimeResourceSnapshot | None = None
    runtime: RuntimeCapability | None = None


class RuntimeChatResponse(VersionedModel):
    model: str
    provider: str
    content: str
    correlation_id: str
    route: RuntimeDecision
    provenance: dict[str, Any] = Field(default_factory=dict)


class RuntimeGenerateResponse(RuntimeChatResponse):
    pass


class RuntimeEmbeddingResponse(VersionedModel):
    model: str
    provider: str
    vectors: list[list[float]]
    correlation_id: str
    route: RuntimeDecision
    provenance: dict[str, Any] = Field(default_factory=dict)


class RuntimeRequestContext(BaseModel):
    principal: str = "gaia"
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class RuntimeExecutionResult:
    content: str
    model: str
    provider: str
    correlation_id: str
    route: RuntimeDecision
    provenance: dict[str, Any]
    available: bool = True
    warnings: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


class LocalAIRuntimeClient:
    def __init__(
        self,
        settings: LocalAIRuntimeSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        client_factory: type[httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        self.settings = settings
        self.base_url = str(settings.base_url).rstrip("/")
        parsed = urlparse(self.base_url)
        if settings.require_local_only and not _is_loopback_host(parsed.hostname):
            raise ValueError("Local AI Runtime must be loopback-only")
        self.api_base = f"{self.base_url}/{settings.api_version.lstrip('/')}"
        self._transport = transport
        self._client_factory = client_factory

    async def health(self) -> RuntimeHealthResponse:
        payload = await self._json("GET", "/health")
        return RuntimeHealthResponse.model_validate(payload)

    async def status(self) -> RuntimeStatusResponse:
        payload = await self._json("GET", f"/{self.settings.api_version}/status")
        return RuntimeStatusResponse.model_validate(payload)

    async def models(self) -> RuntimeModelListResponse:
        payload = await self._json("GET", f"/{self.settings.api_version}/models")
        return RuntimeModelListResponse.model_validate(payload)

    async def route_explain(
        self,
        *,
        task: str,
        model: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeDecision:
        payload = await self._json(
            "POST",
            f"/{self.settings.api_version}/route/explain",
            json={
                "principal": "gaia",
                "task": task,
                "model": model,
                "correlation_id": correlation_id,
                "metadata": metadata or {},
            },
        )
        return RuntimeRouteExplainResponse.model_validate(payload).decision

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        task: str = "chat",
        model: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> RuntimeChatResponse:
        payload = await self._json(
            "POST",
            f"/{self.settings.api_version}/chat",
            json={
                "principal": "gaia",
                "task": task,
                "messages": messages,
                "model": model,
                "correlation_id": correlation_id,
                "metadata": metadata or {},
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        return RuntimeChatResponse.model_validate(payload)

    async def generate(
        self,
        *,
        prompt: str,
        task: str = "generate",
        model: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> RuntimeGenerateResponse:
        payload = await self._json(
            "POST",
            f"/{self.settings.api_version}/generate",
            json={
                "principal": "gaia",
                "task": task,
                "prompt": prompt,
                "model": model,
                "correlation_id": correlation_id,
                "metadata": metadata or {},
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        return RuntimeGenerateResponse.model_validate(payload)

    async def embeddings(
        self,
        *,
        texts: list[str],
        model: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeEmbeddingResponse:
        payload = await self._json(
            "POST",
            f"/{self.settings.api_version}/embeddings",
            json={
                "principal": "gaia",
                "texts": texts,
                "model": model,
                "correlation_id": correlation_id,
                "metadata": metadata or {},
            },
        )
        return RuntimeEmbeddingResponse.model_validate(payload)

    async def _json(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        timeout = httpx.Timeout(
            self.settings.request_timeout_seconds,
            connect=self.settings.connection_timeout_seconds,
        )
        try:
            async with self._client_factory(base_url=self.base_url, timeout=timeout, transport=self._transport) as client:
                response = await client.request(method, path, json=json)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise LocalAIRuntimeUnavailable(f"Local AI Runtime request timed out: {type(exc).__name__}") from exc
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail_payload = exc.response.json()
                if isinstance(detail_payload, dict):
                    detail = str(detail_payload.get("message") or detail_payload.get("detail") or "")
            except Exception:
                detail = ""
            raise LocalAIRuntimeHTTPError(detail or f"Runtime request failed with HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise LocalAIRuntimeUnavailable(f"Local AI Runtime unavailable: {type(exc).__name__}") from exc
        except Exception as exc:
            raise LocalAIRuntimeHTTPError(f"Local AI Runtime request failed: {type(exc).__name__}") from exc
        if not isinstance(payload, dict):
            raise LocalAIRuntimeSchemaError("Local AI Runtime returned a non-object JSON payload")
        return payload


def load_local_ai_runtime(path: str | Path | None = None) -> LocalAIRuntimeSettings:
    resolved = Path(path or "config/model-routing.yaml")
    if not resolved.exists():
        return LocalAIRuntimeSettings()
    raw = resolved.read_text(encoding="utf-8")
    import yaml

    parsed = yaml.safe_load(raw) or {}
    if not isinstance(parsed, dict):
        raise ValueError("Local AI Runtime configuration must be a mapping")
    if isinstance(parsed.get("local_ai_runtime"), dict):
        parsed = parsed["local_ai_runtime"]
    elif isinstance(parsed.get("model_routing"), dict):
        parsed = parsed["model_routing"]
    if not isinstance(parsed, dict):
        raise ValueError("Local AI Runtime configuration must be a mapping")

    base_url = parsed.get("base_url")
    if base_url is None:
        providers = parsed.get("providers", {})
        if isinstance(providers, dict):
            ollama = providers.get("ollama")
            if isinstance(ollama, dict) and ollama.get("base_url") is not None:
                base_url = ollama.get("base_url")

    settings_data = {
        "enabled": bool(parsed.get("enabled", True)),
        "base_url": base_url or "http://127.0.0.1:8787",
        "api_version": parsed.get("api_version", API_VERSION),
        "request_timeout_seconds": float(parsed.get("request_timeout_seconds", 30.0)),
        "connection_timeout_seconds": float(parsed.get("connection_timeout_seconds", 5.0)),
        "require_local_only": bool(parsed.get("require_local_only", True)),
    }
    return LocalAIRuntimeSettings(**settings_data)
