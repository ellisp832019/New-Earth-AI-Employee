from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from gaia.config import load_settings
from gaia.db import Database
from gaia.service import ProjectService


def _service(settings_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectService:
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / "gaia.db"))
    settings = load_settings(settings_path)
    database = Database(settings.database_path)
    return ProjectService(settings, database)


def _write_settings(tmp_path: Path, project_id: str, root: Path) -> Path:
    settings_path = tmp_path / f"{project_id}.yaml"
    payload = {
        "projects": {
            project_id: {
                "name": project_id.title(),
                "root": str(root),
                "access": "read_only",
                "approved_extensions": [".md", ".txt"],
                "excluded_directories": [".git", ".venv"],
                "excluded_filenames": [".env"],
                "important_paths": ["README.md", "docs"],
                "health_rules": {"evidence_freshness_hours": 24, "required_paths": ["README.md", "docs"]},
                "release_rules": {"assume_unknown_when_no_upstream": True},
                "approval_requirements": {"registry_review": "required"},
            }
        }
    }
    settings_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return settings_path


def _active_recommendation(service: ProjectService, project_id: str):
    recommendations = service.generate_project_recommendations(project_id)
    return next(item for item in recommendations if item.lifecycle_state == "active")


def test_generates_reviewable_work_package_from_active_recommendation(
    settings_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(settings_file, tmp_path, monkeypatch)
    try:
        service.project_health("sample")
        recommendation = _active_recommendation(service, "sample")
        package = service.generate_work_package(recommendation.recommendation_id)
        revision = service.work_package_revisions(package.work_package_id)[0]

        assert package.source_recommendation_id == recommendation.recommendation_id
        assert package.approval_state == "proposed"
        assert package.gate_state == "open"
        assert package.current_revision_number == 1
        assert package.current_revision_id == revision.revision_id
        assert package.approval_target_fingerprint == revision.approval_target_fingerprint
        assert package.package_fingerprint == revision.package_fingerprint
        assert package.content_fingerprint == package.package_fingerprint
        assert service.work_package_summary(package.work_package_id)["current_revision_number"] == 1
        prompt = service.render_work_package_prompt(package.work_package_id)
        assert "DO NOT EXECUTE THIS PROMPT AUTOMATICALLY." in prompt
        assert "STOP:" in prompt
        assert '"evidence_kind"' in prompt
    finally:
        service.database.close()


def test_generates_blocked_package_but_keeps_review_gate_closed(
    sample_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_root = tmp_path / "missing-root"
    settings_path = _write_settings(tmp_path, "blocked", missing_root)
    service = _service(settings_path, tmp_path, monkeypatch)
    try:
        service.project_health("blocked")
        recommendation = service.generate_project_recommendations("blocked")[0].model_copy(
            update={
                "recommendation_id": f"{service.generate_project_recommendations('blocked')[0].recommendation_id}-blocked",
                "lifecycle_state": "blocked",
            }
        )
        service.database.insert_project_recommendation(recommendation)
        package = service.generate_work_package(recommendation.recommendation_id)

        assert package.approval_state == "proposed"
        assert package.gate_state == "blocked"
        assert package.source_recommendation_lifecycle_state == "blocked"
        with pytest.raises(ValueError, match="Blocked work packages cannot be approved or handed off"):
            service.work_package_submit_for_review(package.work_package_id, package.current_revision_number)
    finally:
        service.database.close()


def test_insufficient_evidence_recommendation_cannot_be_packaged(
    settings_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(settings_file, tmp_path, monkeypatch)
    try:
        recommendation = next(
            item for item in service.generate_project_recommendations("sample") if item.recommendation_type == "insufficient_evidence"
        )
        with pytest.raises(ValueError, match="Insufficient-evidence recommendations cannot be turned into work packages"):
            service.generate_work_package(recommendation.recommendation_id)
    finally:
        service.database.close()


def test_work_package_approval_handoff_and_outcome_are_bound_to_exact_revision(
    settings_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(settings_file, tmp_path, monkeypatch)
    try:
        service.project_health("sample")
        recommendation = _active_recommendation(service, "sample")
        package = service.generate_work_package(recommendation.recommendation_id)

        package = service.work_package_submit_for_review(package.work_package_id, package.current_revision_number, actor="reviewer")
        approved = service.work_package_approve(
            package.work_package_id,
            package.current_revision_number,
            actor="reviewer",
            human_note="Approved for review package handoff.",
        )
        decisions = service.work_package_approval_decisions(package.work_package_id)
        assert approved.approval_state == "approved"
        assert len(decisions) == 1
        assert decisions[0].decision == "approved"
        assert decisions[0].revision_number == package.current_revision_number

        handed_off = service.work_package_handoff(package.work_package_id, package.current_revision_number, approved_by="reviewer")
        handoffs = service.work_package_handoffs(package.work_package_id)
        assert handed_off.approval_state == "handed_off"
        assert len(handoffs) == 1
        assert handoffs[0].approval_decision_id == decisions[0].decision_id
        assert handoffs[0].approval_target_fingerprint == package.approval_target_fingerprint

        completed = service.work_package_record_outcome(
            package.work_package_id,
            package.current_revision_number,
            outcome="completed",
            actor="runner",
            note="Validation passed.",
        )
        outcomes = service.work_package_outcomes(package.work_package_id)
        assert completed.approval_state == "completed"
        assert len(outcomes) == 1
        assert outcomes[0].outcome == "completed"
        assert outcomes[0].approval_target_fingerprint == package.approval_target_fingerprint
    finally:
        service.database.close()


def test_revise_work_package_creates_new_revision_without_transferring_approval(
    settings_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(settings_file, tmp_path, monkeypatch)
    try:
        service.project_health("sample")
        recommendation = _active_recommendation(service, "sample")
        package = service.generate_work_package(recommendation.recommendation_id)
        package = service.work_package_submit_for_review(package.work_package_id, package.current_revision_number, actor="reviewer")
        service.work_package_approve(
            package.work_package_id,
            package.current_revision_number,
            actor="reviewer",
            human_note="Approved before revision.",
        )
        revised = service.revise_work_package(
            package.work_package_id,
            change_reason="Expand validation coverage",
            field_updates={"validation_plan": [*package.validation_plan, "python -m pytest tests/test_work_packages.py"]},
            actor="reviewer",
        )
        revisions = service.work_package_revisions(package.work_package_id)
        decisions = service.work_package_approval_decisions(package.work_package_id)

        assert revised.current_revision_number == 2
        assert revised.approval_state == "proposed"
        assert len(revisions) == 2
        assert revisions[0].revision_number == 2
        assert revisions[1].revision_number == 1
        assert revisions[0].previous_revision_id == revisions[1].revision_id
        assert decisions[0].revision_number == 1
        assert revised.current_revision_id == revisions[0].revision_id
    finally:
        service.database.close()


def test_detect_work_package_staleness_tracks_source_drift(
    settings_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(settings_file, tmp_path, monkeypatch)
    repo_root = Path(load_settings(settings_file).projects["sample"].root)
    try:
        service.project_health("sample")
        recommendation = _active_recommendation(service, "sample")
        package = service.generate_work_package(recommendation.recommendation_id)

        (repo_root / "README.md").write_text("# Sample\nChanged for staleness.\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "staleness change"], cwd=repo_root, check=True, capture_output=True)
        service.project_health("sample")

        refreshed = service.detect_work_package_staleness(package.work_package_id)
        assert refreshed.staleness_state == "stale"
        assert refreshed.staleness_reason is not None
        with pytest.raises(ValueError, match="Stale or expired work packages cannot transition"):
            service.work_package_submit_for_review(package.work_package_id, package.current_revision_number)
    finally:
        service.database.close()
