from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from gaia.config import load_settings


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-project"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("# Sample\nMicroGrow project control evidence.", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "status.md").write_text("Current branch is a test fixture.", encoding="utf-8")
    (repo / ".env").write_text("SECRET=do-not-index", encoding="utf-8")
    (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", "docs/status.md", ".gitignore"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    return repo


@pytest.fixture
def settings_file(tmp_path: Path, sample_repo: Path) -> Path:
    config = {
        "projects": {
            "sample": {
                "name": "Sample",
                "root": str(sample_repo),
                "access": "read_only",
                "approved_extensions": [".md", ".txt", ".json"],
                "excluded_directories": [".git", "build", ".venv"],
                "excluded_filenames": [".env", "credentials.json"],
                "important_paths": ["README.md", "docs", "missing.md"],
            }
        }
    }
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


@pytest.fixture
def settings(settings_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / "gaia.db"))
    return load_settings(settings_file)
