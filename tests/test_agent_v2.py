import asyncio
import subprocess
from pathlib import Path

from gaia.agent import AgentService
from gaia.config import load_settings
from gaia.db import Database
from gaia.providers import ProviderRegistry
from gaia.service import ProjectService


def test_agent_ask_persists_run(settings):
    database = Database(settings.database_path)
    service = AgentService(
        project_service=ProjectService(settings, database),
        database=database,
        provider_registry=ProviderRegistry(settings.model_routing),
    )
    response = asyncio.run(service.ask("sample", "What was completed most recently?", deterministic_only=True))
    assert response.project_id == "sample"
    assert response.run_id
    runs = database.list_agent_runs()
    assert runs and runs[0]["run_id"] == response.run_id
    database.close()


def test_agent_ollama_fallback(settings):
    database = Database(settings.database_path)
    service = AgentService(
        project_service=ProjectService(settings, database),
        database=database,
        provider_registry=ProviderRegistry(settings.model_routing),
    )
    response = asyncio.run(service.ask("sample", "Where exactly is MicroGrow currently?", provider="ollama"))
    assert response.deterministic_only is True
    assert response.answer
    database.close()


def test_conversational_run_is_read_only(tmp_path, monkeypatch):
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / "gaia.db"))
    settings = load_settings(Path("config/projects.yaml"))
    project = settings.projects["microgrow-v1"]
    before = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=project.root, text=True, capture_output=True, check=True
    ).stdout
    database = Database(settings.database_path)
    service = AgentService(
        project_service=ProjectService(settings, database),
        database=database,
        provider_registry=ProviderRegistry(settings.model_routing),
    )
    response = asyncio.run(service.ask("microgrow-v1", "What was completed most recently?", deterministic_only=True))
    after = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=project.root, text=True, capture_output=True, check=True
    ).stdout
    assert response.project_id == "microgrow-v1"
    assert before == after
    database.close()
