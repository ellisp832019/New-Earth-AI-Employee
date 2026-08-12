from __future__ import annotations

import asyncio

import httpx
import pytest

from gaia.conversation import EvidenceItem, ModelRequest, QuestionAnalysis
from gaia.local_ai_runtime import LocalAIRuntimeClient, LocalAIRuntimeSettings
from gaia.providers import MockModelProvider, ProviderRegistry


def _runtime_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/health":
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "service": "new-earth-local-ai-runtime",
                "version": "v1",
                "local_only": True,
                "providers": {"ollama": True, "mock": True},
                "runtime": {
                    "service": "new-earth-local-ai-runtime",
                    "version": "v1",
                    "local_only": True,
                    "capabilities": ["chat", "generate", "embeddings", "route-explain"],
                    "api_base": "http://127.0.0.1:8787/v1",
                    "providers": ["ollama", "mock"],
                    "selected_default_model": "chat-local-default",
                },
            },
        )
    if path == "/v1/status":
        return httpx.Response(
            200,
            json={
                "service": "new-earth-local-ai-runtime",
                "version": "v1",
                "local_only": True,
                "host": "127.0.0.1",
                "port": 8787,
                "api_base": "http://127.0.0.1:8787/v1",
                "selected_default_model": "chat-local-default",
                "selected_embedding_model": "embedding-local-default",
                "providers": {"ollama": True, "mock": True},
                "resources": None,
                "runtime": {
                    "service": "new-earth-local-ai-runtime",
                    "version": "v1",
                    "local_only": True,
                    "capabilities": ["chat", "generate", "embeddings", "route-explain"],
                    "api_base": "http://127.0.0.1:8787/v1",
                    "providers": ["ollama", "mock"],
                    "selected_default_model": "chat-local-default",
                },
            },
        )
    if path == "/v1/models":
        return httpx.Response(
            200,
            json={
                "service": "new-earth-local-ai-runtime",
                "version": "v1",
                "models": [
                    {
                        "id": "chat-local-default",
                        "display_name": "Local Chat Default",
                        "provider": "ollama",
                        "provider_model_name": "qwen2.5:7b",
                        "purpose": "conversational",
                        "task_types": ["chat", "generate", "reasoning"],
                        "enabled": True,
                        "preferred": True,
                    }
                ],
            },
        )
    if path == "/v1/route/explain":
        return httpx.Response(
            200,
            json={
                "decision": {
                    "requested_task": "chat",
                    "requested_model": None,
                    "selected_model": "chat-local-default",
                    "selected_provider": "ollama",
                    "provider_model_name": "qwen2.5:7b",
                    "reason": "configured route",
                    "fallback_used": False,
                    "resource_constraints": {},
                    "resource_snapshot": None,
                }
            },
        )
    if path == "/v1/chat":
        return httpx.Response(
            200,
            json={
                "model": "chat-local-default",
                "provider": "ollama",
                "content": "runtime answer",
                "correlation_id": "corr-1",
                "route": {
                    "requested_task": "chat",
                    "requested_model": None,
                    "selected_model": "chat-local-default",
                    "selected_provider": "ollama",
                    "provider_model_name": "qwen2.5:7b",
                    "reason": "configured route",
                    "fallback_used": False,
                    "resource_constraints": {},
                    "resource_snapshot": None,
                },
                "provenance": {"provider": "ollama", "route_reason": "configured route"},
            },
        )
    if path == "/v1/generate":
        return httpx.Response(
            200,
            json={
                "model": "chat-local-default",
                "provider": "ollama",
                "content": "generated runtime answer",
                "correlation_id": "corr-2",
                "route": {
                    "requested_task": "generate",
                    "requested_model": None,
                    "selected_model": "chat-local-default",
                    "selected_provider": "ollama",
                    "provider_model_name": "qwen2.5:7b",
                    "reason": "configured route",
                    "fallback_used": False,
                    "resource_constraints": {},
                    "resource_snapshot": None,
                },
                "provenance": {"provider": "ollama", "route_reason": "configured route"},
            },
        )
    if path == "/v1/embeddings":
        return httpx.Response(
            200,
            json={
                "model": "embedding-local-default",
                "provider": "ollama",
                "vectors": [[0.1, 0.2], [0.3, 0.4]],
                "correlation_id": "corr-3",
                "route": {
                    "requested_task": "embedding",
                    "requested_model": None,
                    "selected_model": "embedding-local-default",
                    "selected_provider": "ollama",
                    "provider_model_name": "nomic-embed-text",
                    "reason": "configured route",
                    "fallback_used": False,
                    "resource_constraints": {},
                    "resource_snapshot": None,
                },
                "provenance": {"provider": "ollama"},
            },
        )
    return httpx.Response(404, json={"message": f"Unexpected path: {path}"})


def _runtime_client() -> LocalAIRuntimeClient:
    settings = LocalAIRuntimeSettings()
    transport = httpx.MockTransport(_runtime_handler)
    return LocalAIRuntimeClient(settings, transport=transport)


def test_mock_model_provider_generates_answer():
    provider = MockModelProvider()
    request = ModelRequest(
        system_prompt="system",
        user_question="What happened?",
        analysis=QuestionAnalysis(category="general"),
        evidence=[
            EvidenceItem(
                source_kind="document",
                project_id="sample",
                source_path="README.md",
                title="README",
                snippet="MicroGrow project control evidence.",
            )
        ],
        model_name="mock",
        endpoint_identity="mock",
        timeout_seconds=30,
        max_response_bytes=1000,
        max_context_chars=1000,
    )
    response = asyncio.run(provider.generate(request))
    assert response.available is True
    assert "Facts:" in response.content
    assert response.provider == "deterministic"


def test_runtime_client_rejects_non_loopback():
    with pytest.raises(ValueError):
        LocalAIRuntimeClient(LocalAIRuntimeSettings(base_url="http://example.com"))


def test_runtime_client_health_status_models_and_execution():
    client = _runtime_client()
    health, status, models, route = asyncio.run(
        _exercise_runtime(client)
    )
    assert health.status == "ok"
    assert status.selected_default_model == "chat-local-default"
    assert models.models[0].id == "chat-local-default"
    assert route.selected_model == "chat-local-default"


async def _exercise_runtime(client: LocalAIRuntimeClient):
    health = await client.health()
    status = await client.status()
    models = await client.models()
    route = await client.route_explain(task="chat")
    chat = await client.chat(messages=[{"role": "user", "content": "hello"}], task="chat")
    generate = await client.generate(prompt="say hello")
    embeddings = await client.embeddings(texts=["hello", "world"])
    assert chat.provider == "ollama"
    assert generate.provider == "ollama"
    assert len(embeddings.vectors) == 2
    return health, status, models, route


def test_legacy_provider_registry_routes_to_runtime_or_deterministic():
    registry = ProviderRegistry(LocalAIRuntimeSettings(), _runtime_client())
    runtime_selection = registry.select("ollama")
    mock_selection = registry.select("mock")
    assert runtime_selection.name == "runtime"
    assert mock_selection.name == "deterministic"
