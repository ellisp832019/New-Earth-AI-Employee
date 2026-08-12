from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from gaia.conversation import ModelRequest, ModelResponse, ModelStatus, assemble_context
from gaia.local_ai_runtime import (
    LocalAIRuntimeClient,
    LocalAIRuntimeSettings,
    LocalAIRuntimeUnavailable,
)


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
            provider="deterministic",
            model_name=self.model_name,
            endpoint_identity="local-deterministic",
            content=content,
            usage={"prompt_chars": len(request.system_prompt) + len(request.user_question)},
            warnings=[],
            available=True,
        )

    async def status(self) -> ModelStatus:
        return ModelStatus(
            provider="deterministic",
            available=True,
            model_name=self.model_name,
            endpoint_identity="local-deterministic",
            details="Deterministic local fallback",
        )


class RuntimeExecutionProvider:
    def __init__(self, client: LocalAIRuntimeClient) -> None:
        self.client = client

    async def generate(self, request: ModelRequest) -> ModelResponse:
        task = _canonical_task_name(request.analysis.category)
        prompt = _render_prompt(request)
        try:
            route = await self.client.route_explain(task=task, model=request.model_name or None)
            runtime_response = await self.client.generate(
                prompt=prompt,
                task=task,
                model=route.selected_model,
                correlation_id=request.endpoint_identity or None,
                metadata={
                    "analysis": request.analysis.model_dump(mode="json"),
                    "evidence_count": len(request.evidence),
                },
            )
        except LocalAIRuntimeUnavailable as exc:
            return ModelResponse(
                provider="runtime",
                model_name=request.model_name or None,
                endpoint_identity=self.client.api_base,
                content="",
                available=False,
                error=str(exc),
            )
        except Exception as exc:
            return ModelResponse(
                provider="runtime",
                model_name=request.model_name or None,
                endpoint_identity=self.client.api_base,
                content="",
                available=False,
                error=type(exc).__name__,
            )
        content = runtime_response.content or _render_prompt(request)
        return ModelResponse(
            provider=runtime_response.provider,
            model_name=runtime_response.model,
            endpoint_identity=self.client.api_base,
            content=content,
            usage={
                "correlation_id": runtime_response.correlation_id,
                "route_reason": runtime_response.route.reason,
                "fallback_used": runtime_response.route.fallback_used,
                "selected_provider": runtime_response.route.selected_provider,
                "selected_model": runtime_response.route.selected_model,
            },
            warnings=[],
            available=True,
        )

    async def status(self) -> ModelStatus:
        try:
            runtime_status = await self.client.status()
            runtime_health = await self.client.health()
        except Exception as exc:
            return ModelStatus(
                provider="runtime",
                available=False,
                model_name=None,
                endpoint_identity=self.client.api_base,
                details=str(exc),
            )
        details: str = runtime_health.status
        if runtime_status.selected_default_model:
            details = f"{details}; default={runtime_status.selected_default_model}"
        return ModelStatus(
            provider="runtime",
            available=runtime_health.status != "fail",
            model_name=runtime_status.selected_default_model,
            endpoint_identity=runtime_status.api_base,
            details=details,
        )


@dataclass(slots=True)
class ProviderSelection:
    name: str
    provider: ModelProvider
    model_name: str | None


class ProviderRegistry:
    def __init__(self, routing: LocalAIRuntimeSettings, client: LocalAIRuntimeClient | None = None) -> None:
        self.routing = routing
        self.mock = MockModelProvider()
        self.runtime_client = client or LocalAIRuntimeClient(routing)
        self.runtime = RuntimeExecutionProvider(self.runtime_client)

    def select(self, provider_name: str | None = None) -> ProviderSelection:
        name = (provider_name or "").strip().lower()
        if name in {"mock", "deterministic", "none"}:
            return ProviderSelection("deterministic", self.mock, self.mock.model_name)
        return ProviderSelection("runtime", self.runtime, None)

    async def list_status(self) -> list[ModelStatus]:
        return [await self.runtime.status(), await self.mock.status()]


def _render_prompt(request: ModelRequest) -> str:
    evidence_text = "\n".join(
        f"- {item.source_path}: {item.snippet[:240]}" for item in request.evidence[:10]
    ) or "- No evidence selected"
    context = assemble_context(
        request.user_question,
        request.analysis,
        request.evidence,
        snapshot_id=request.endpoint_identity,
        project_id="gaia",
    )
    return (
        f"{request.system_prompt}\n\n"
        "Evidence:\n"
        f"{evidence_text}\n\n"
        "Context:\n"
        f"{context}\n\n"
        "Answer the question with explicit fact/inference separation."
    )


def _canonical_task_name(task: str) -> str:
    return task.strip().lower().replace("_", "-")
