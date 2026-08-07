from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
import yaml

from gaia.config import load_settings
from gaia.db import Database
from gaia.recommendations import validate_recommendation_dependencies
from gaia.service import ProjectService


def _write_settings(tmp_path: Path, projects: dict[str, dict[str, object]]) -> Path:
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump({"projects": projects}, sort_keys=False), encoding="utf-8")
    return path


def _service(tmp_path: Path, settings_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectService:
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / "gaia.db"))
    settings = load_settings(settings_path)
    database = Database(settings.database_path)
    return ProjectService(settings, database)


def _close(service: ProjectService) -> None:
    service.database.close()


def _rootless_project(tmp_path: Path) -> dict[str, object]:
    return {
        "name": "Rootless",
        "root": str(tmp_path / "missing-root"),
        "access": "read_only",
        "enabled": True,
        "repository_type": "git",
        "inspection_access": "read_only",
        "output_access": "none",
        "sensitivity": "internal",
        "approved_extensions": [".md", ".txt"],
        "excluded_directories": [".git", ".venv"],
        "excluded_filenames": [".env"],
        "important_paths": ["README.md"],
        "health_rules": {"evidence_freshness_hours": 24, "required_paths": ["README.md"]},
        "release_rules": {"assume_unknown_when_no_upstream": True},
        "approval_requirements": {"registry_review": "required"},
        "metadata": {"owner": "rootless"},
    }


def test_recommendations_are_deterministic_for_identical_evidence(
    settings_file: Path, tmp_path: Path, sample_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, settings_file, monkeypatch)
    try:
        service.project_health("sample")
        first = service.generate_project_recommendations("sample")
        second = service.generate_project_recommendations("sample")
        assert [item.recommendation_id for item in first] == [item.recommendation_id for item in second]
        assert [item.deterministic_score for item in first] == [item.deterministic_score for item in second]
        assert len(service.list_project_recommendations("sample")) == len(first)
    finally:
        _close(service)


def test_blocking_project_generates_p0_recommendation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings_path = _write_settings(tmp_path, {"rootless": _rootless_project(tmp_path)})
    service = _service(tmp_path, settings_path, monkeypatch)
    try:
        service.project_health("rootless")
        recommendations = service.generate_project_recommendations("rootless")
        assert recommendations
        primary = next(item for item in recommendations if item.recommendation_type == "review_blocking_project_health_condition")
        assert primary.priority_tier == "P0"
        assert primary.lifecycle_state == "active"
        assert primary.score_breakdown.total_score >= 90
    finally:
        _close(service)


def test_stale_evidence_blocks_follow_up_recommendations(
    settings_file: Path, tmp_path: Path, sample_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, settings_file, monkeypatch)
    try:
        snapshot = service.snapshot("sample")
        stale_snapshot = snapshot.model_copy(update={"created_at": snapshot.created_at - timedelta(days=3)})
        service.database.insert_snapshot(stale_snapshot)
        service.project_health("sample")
        recommendations = service.generate_project_recommendations("sample")
        refresh = next(item for item in recommendations if item.recommendation_type == "refresh_project_evidence_before_relying_on_state")
        assert refresh.lifecycle_state == "active"
        blocked_follow_ups = [item for item in recommendations if item.recommendation_type != refresh.recommendation_type]
        assert blocked_follow_ups
        assert all(item.lifecycle_state in {"blocked", "superseded"} for item in blocked_follow_ups)
        assert all(refresh.recommendation_id in item.dependencies or not item.dependencies for item in blocked_follow_ups)
    finally:
        _close(service)


def test_lifecycle_resolves_when_issue_disappears(
    settings_file: Path, tmp_path: Path, sample_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, settings_file, monkeypatch)
    try:
        service.project_health("sample")
        initial = service.generate_project_recommendations("sample")
        important = next(item for item in initial if item.recommendation_type == "verify_removal_of_configured_important_project_path")
        (sample_repo / "missing.md").write_text("restored\n", encoding="utf-8")
        service.project_health("sample")
        refreshed = service.generate_project_recommendations("sample")
        resolved = next(item for item in refreshed if item.recommendation_id == important.recommendation_id)
        assert resolved.lifecycle_state == "resolved"
    finally:
        _close(service)


def test_queue_order_is_stable_and_dependency_aware(
    settings_file: Path, tmp_path: Path, sample_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, settings_file, monkeypatch)
    try:
        snapshot = service.snapshot("sample")
        stale_snapshot = snapshot.model_copy(update={"created_at": snapshot.created_at - timedelta(days=3)})
        service.database.insert_snapshot(stale_snapshot)
        service.project_health("sample")
        queue = service.recommendation_queue("sample")
        assert queue[0].recommendation_type == "refresh_project_evidence_before_relying_on_state"
        assert any(item.lifecycle_state in {"blocked", "superseded"} for item in queue[1:])
    finally:
        _close(service)


def test_repeated_refresh_does_not_duplicate_records(
    settings_file: Path, tmp_path: Path, sample_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, settings_file, monkeypatch)
    try:
        service.project_health("sample")
        first = service.generate_project_recommendations("sample")
        second = service.generate_project_recommendations("sample")
        assert len(service.list_project_recommendations("sample")) == len(first)
        assert {item.recommendation_id for item in first} == {item.recommendation_id for item in second}
    finally:
        _close(service)


def test_unknown_evidence_does_not_become_high_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings_path = _write_settings(tmp_path, {"rootless": _rootless_project(tmp_path)})
    service = _service(tmp_path, settings_path, monkeypatch)
    try:
        recommendations = service.generate_project_recommendations("rootless")
        assert recommendations[0].recommendation_type == "insufficient_evidence"
        assert recommendations[0].priority_tier in {"P3", "P4"}
    finally:
        _close(service)


def test_dependency_cycle_detection_fails_closed(
    settings_file: Path, tmp_path: Path, sample_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, settings_file, monkeypatch)
    try:
        service.project_health("sample")
        recommendations = service.generate_project_recommendations("sample")
        base = recommendations[0]
        left = base.model_copy(update={"recommendation_id": "left", "dependencies": ["right"]})
        right = base.model_copy(update={"recommendation_id": "right", "dependencies": ["left"]})
        with pytest.raises(ValueError, match="Recommendation dependency cycle detected"):
            validate_recommendation_dependencies([left, right])
    finally:
        _close(service)
