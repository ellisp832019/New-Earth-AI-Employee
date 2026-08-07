from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from gaia.models import ProjectConfig
from gaia.routing import ModelRoutingSettings, load_model_routing


class Settings(BaseModel):
    config_path: Path = Path("config/projects.yaml")
    database_path: Path = Path("data/gaia.db")
    signing_key_store: Path = Path("data/signing-keys")
    model_routing_path: Path = Path("config/model-routing.yaml")
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    signing_enabled: bool = False
    max_file_bytes: int = 2_000_000
    max_git_output_bytes: int = 1_000_000
    git_timeout_seconds: int = 15
    projects: dict[str, ProjectConfig] = Field(default_factory=dict)
    model_routing: ModelRoutingSettings = Field(default_factory=ModelRoutingSettings)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def load_settings(config_path: str | Path | None = None) -> Settings:
    path = Path(config_path or _env("GAIA_CONFIG_PATH", "config/projects.yaml"))
    raw: dict[str, Any] = {}
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Project configuration must be a mapping")
        raw = loaded

    projects: dict[str, ProjectConfig] = {}
    project_map = raw.get("projects", {})
    if not isinstance(project_map, dict):
        raise ValueError("'projects' must be a mapping")

    for project_id, value in project_map.items():
        if not isinstance(value, dict):
            raise ValueError(f"Project '{project_id}' must be a mapping")
        projects[project_id] = ProjectConfig(project_id=project_id, **value)

    _validate_project_roots(projects)

    return Settings(
        config_path=path,
        database_path=Path(_env("GAIA_DATABASE_PATH", "data/gaia.db")),
        signing_key_store=Path(_env("GAIA_SIGNING_KEY_STORE", "data/signing-keys")),
        model_routing_path=Path(_env("GAIA_MODEL_ROUTING_PATH", "config/model-routing.yaml")),
        log_level=_env("GAIA_LOG_LEVEL", "INFO"),
        api_host=_env("GAIA_API_HOST", "127.0.0.1"),
        api_port=int(_env("GAIA_API_PORT", "8765")),
        signing_enabled=_env("GAIA_SIGNING_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        max_file_bytes=int(_env("GAIA_MAX_FILE_BYTES", "2000000")),
        max_git_output_bytes=int(_env("GAIA_MAX_GIT_OUTPUT_BYTES", "1000000")),
        git_timeout_seconds=int(_env("GAIA_GIT_TIMEOUT_SECONDS", "15")),
        projects=projects,
        model_routing=load_model_routing(Path(_env("GAIA_MODEL_ROUTING_PATH", "config/model-routing.yaml"))),
    )


def _validate_project_roots(projects: dict[str, ProjectConfig]) -> None:
    seen: dict[str, str] = {}
    for project_id, project in projects.items():
        canonical = Path(project.root).resolve(strict=False)
        key = str(canonical).casefold()
        other = seen.get(key)
        if other and other != project_id:
            raise ValueError(
                f"Projects '{other}' and '{project_id}' share the same canonical root: {canonical}"
            )
        seen[key] = project_id
