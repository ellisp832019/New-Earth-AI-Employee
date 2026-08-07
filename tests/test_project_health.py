from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

import pytest
import yaml

from gaia.audit import AuditRecorder
from gaia.config import load_settings
from gaia.db import Database
from gaia.project_health import ProjectHealthService


def _init_repo(repo: Path, *, with_remote: bool = False) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("# Project\n", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "status.md").write_text("Initial status.\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", "docs/status.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    if with_remote:
        remote = repo.parent / f"{repo.name}.git"
        subprocess.run(["git", "init", "--bare", str(remote)], cwd=repo.parent, check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=repo, check=True, capture_output=True)
    return repo


def _write_settings(tmp_path: Path, projects: dict[str, dict[str, object]]) -> Path:
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump({"projects": projects}, sort_keys=False), encoding="utf-8")
    return path


def _service_for(config_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / "gaia.db"))
    settings = load_settings(config_path)
    database = Database(settings.database_path)
    return ProjectHealthService(settings, database, AuditRecorder(database)), database, settings


def _project_settings(repo: Path, *, enabled: bool = True) -> dict[str, object]:
    return {
        "name": repo.name,
        "root": str(repo),
        "access": "read_only",
        "enabled": enabled,
        "repository_type": "git",
        "inspection_access": "read_only",
        "output_access": "none",
        "sensitivity": "internal",
        "approved_extensions": [".md", ".txt"],
        "excluded_directories": [".git", ".venv"],
        "excluded_filenames": [".env"],
        "important_paths": ["README.md", "docs"],
        "health_rules": {"evidence_freshness_hours": 24, "required_paths": ["README.md", "docs"]},
        "release_rules": {"assume_unknown_when_no_upstream": True},
        "approval_requirements": {"registry_review": "required"},
        "metadata": {"owner": repo.name},
    }


def test_captures_multi_project_portfolio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    healthy_repo = _init_repo(tmp_path / "healthy", with_remote=True)
    dirty_repo = _init_repo(tmp_path / "dirty", with_remote=True)
    (dirty_repo / "README.md").write_text("# changed\n", encoding="utf-8")
    disabled_repo = _init_repo(tmp_path / "disabled", with_remote=True)
    config = _write_settings(
        tmp_path,
        {
            "healthy": _project_settings(healthy_repo),
            "dirty": _project_settings(dirty_repo),
            "disabled": _project_settings(disabled_repo, enabled=False),
        },
    )
    service, database, _ = _service_for(config, tmp_path, monkeypatch)
    try:
        healthy = service.capture_project_health("healthy")
        dirty = service.capture_project_health("dirty")
        portfolio = service.portfolio_view()
        assert healthy.normalized_status == "healthy"
        assert dirty.normalized_status == "attention"
        assert portfolio.enabled_project_count == 2
        assert sorted(entry.project_id for entry in portfolio.projects) == ["dirty", "healthy"]
        assert "disabled" not in portfolio.latest_snapshot_ids
        assert portfolio.projects_without_snapshots == []
        assert portfolio.counts_by_status["healthy"] == 1
        assert portfolio.counts_by_status["attention"] == 1
    finally:
        database.close()


def test_captures_blocked_when_root_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing_root = tmp_path / "missing"
    config = _write_settings(
        tmp_path,
        {
            "missing": {
                "name": "Missing",
                "root": str(missing_root),
                "access": "read_only",
                "approved_extensions": [".md"],
            }
        },
    )
    service, database, _ = _service_for(config, tmp_path, monkeypatch)
    try:
        snapshot = service.capture_project_health("missing")
        assert snapshot.normalized_status == "blocked"
        assert "project_root_missing" in snapshot.reason_codes
    finally:
        database.close()


def test_snapshot_fingerprint_is_stable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    config = _write_settings(tmp_path, {"repo": _project_settings(repo)})
    service, database, _ = _service_for(config, tmp_path, monkeypatch)
    try:
        first = service.capture_project_health("repo")
        second = service.capture_project_health("repo")
        assert first.content_fingerprint == second.content_fingerprint
        assert first.snapshot_id != second.snapshot_id
        latest = service.latest_project_health_snapshot("repo")
        assert latest is not None
        assert latest.snapshot_id == second.snapshot_id
        assert len(service.list_project_health_snapshots("repo")) == 2
    finally:
        database.close()


def test_detached_head_becomes_attention(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    subprocess.run(["git", "switch", "--detach", "HEAD"], cwd=repo, check=True, capture_output=True)
    config = _write_settings(tmp_path, {"repo": _project_settings(repo)})
    service, database, _ = _service_for(config, tmp_path, monkeypatch)
    try:
        snapshot = service.capture_project_health("repo")
        assert snapshot.normalized_status == "attention"
        assert "detached_head" in snapshot.reason_codes
    finally:
        database.close()


def test_schema_migrates_from_version_seven(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA user_version = 7")
    connection.commit()
    connection.close()
    database = Database(db_path)
    try:
        user_version = database.connection.execute("PRAGMA user_version").fetchone()[0]
        table_exists = database.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'project_health_snapshots'"
        ).fetchone()
        assert user_version == 11
        assert table_exists is not None
    finally:
        database.close()
