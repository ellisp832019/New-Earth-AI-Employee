from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from gaia.local_ai_runtime import LocalAIRuntimeSettings, load_local_ai_runtime
from gaia.models import ProjectConfig


class Settings(BaseModel):
    config_path: Path = Path("config/projects.yaml")
    database_path: Path = Path("data/gaia.db")
    signing_key_store: Path = Path("data/signing-keys")
    local_ai_runtime_path: Path = Path("config/model-routing.yaml")
    neos_base_url: str = "http://127.0.0.1:8765"
    neos_timeout_seconds: float = 3.0
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    signing_enabled: bool = False
    max_file_bytes: int = 2_000_000
    max_git_output_bytes: int = 1_000_000
    git_timeout_seconds: int = 15
    projects: dict[str, ProjectConfig] = Field(default_factory=dict)
    local_ai_runtime: LocalAIRuntimeSettings = Field(default_factory=LocalAIRuntimeSettings)

    @property
    def model_routing(self) -> LocalAIRuntimeSettings:
        return self.local_ai_runtime

    @property
    def model_routing_path(self) -> Path:
        return self.local_ai_runtime_path


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

    runtime_path = Path(
        _env(
            "GAIA_LOCAL_AI_RUNTIME_PATH",
            _env("GAIA_MODEL_ROUTING_PATH", "config/model-routing.yaml"),
        )
    )
    runtime_settings = load_local_ai_runtime(runtime_path)
    runtime_url = os.getenv("GAIA_LOCAL_AI_RUNTIME_URL")
    if runtime_url:
        runtime_settings = runtime_settings.model_copy(update={"base_url": runtime_url})
    runtime_api_version = os.getenv("GAIA_LOCAL_AI_RUNTIME_API_VERSION")
    if runtime_api_version:
        runtime_settings = runtime_settings.model_copy(update={"api_version": runtime_api_version})
    runtime_timeout = os.getenv("GAIA_LOCAL_AI_RUNTIME_TIMEOUT_SECONDS")
    if runtime_timeout:
        runtime_settings = runtime_settings.model_copy(update={"request_timeout_seconds": float(runtime_timeout)})
    runtime_connect_timeout = os.getenv("GAIA_LOCAL_AI_RUNTIME_CONNECTION_TIMEOUT_SECONDS")
    if runtime_connect_timeout:
        runtime_settings = runtime_settings.model_copy(update={"connection_timeout_seconds": float(runtime_connect_timeout)})
    runtime_enabled = os.getenv("GAIA_LOCAL_AI_RUNTIME_ENABLED")
    if runtime_enabled:
        runtime_settings = runtime_settings.model_copy(
            update={"enabled": runtime_enabled.lower() in {"1", "true", "yes", "on"}}
        )
    runtime_local_only = os.getenv("GAIA_LOCAL_AI_RUNTIME_REQUIRE_LOCAL_ONLY")
    if runtime_local_only:
        runtime_settings = runtime_settings.model_copy(
            update={"require_local_only": runtime_local_only.lower() in {"1", "true", "yes", "on"}}
        )

    return Settings(
        config_path=path,
        database_path=Path(_env("GAIA_DATABASE_PATH", "data/gaia.db")),
        signing_key_store=Path(_env("GAIA_SIGNING_KEY_STORE", "data/signing-keys")),
        local_ai_runtime_path=runtime_path,
        neos_base_url=_env("GAIA_NEOS_BASE_URL", "http://127.0.0.1:8765"),
        neos_timeout_seconds=float(_env("GAIA_NEOS_TIMEOUT_SECONDS", "3.0")),
        log_level=_env("GAIA_LOG_LEVEL", "INFO"),
        api_host=_env("GAIA_API_HOST", "127.0.0.1"),
        api_port=int(_env("GAIA_API_PORT", "8765")),
        signing_enabled=_env("GAIA_SIGNING_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        max_file_bytes=int(_env("GAIA_MAX_FILE_BYTES", "2000000")),
        max_git_output_bytes=int(_env("GAIA_MAX_GIT_OUTPUT_BYTES", "1000000")),
        git_timeout_seconds=int(_env("GAIA_GIT_TIMEOUT_SECONDS", "15")),
        projects=projects,
        local_ai_runtime=runtime_settings,
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
