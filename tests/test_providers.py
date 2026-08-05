import asyncio

import pytest

from gaia.conversation import EvidenceItem, ModelRequest, QuestionAnalysis
from gaia.providers import MockModelProvider, OllamaModelProvider
from gaia.routing import OllamaProviderConfig


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


def test_ollama_rejects_non_loopback():
    with pytest.raises(ValueError):
        OllamaModelProvider(
            OllamaProviderConfig(enabled=True, base_url="http://example.com", model="llama3.1")
        )
