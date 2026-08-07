from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest
import yaml

from gaia.config import load_settings
from gaia.db import Database
from gaia.models import ProjectHealthSnapshot
from gaia.service import ProjectService


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


def _project_config(repo: Path, *, name: str | None = None) -> dict[str, object]:
    return {
        "name": name or repo.name,
        "root": str(repo),
        "access": "read_only",
        "enabled": True,
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


def _write_settings(tmp_path: Path, projects: dict[str, dict[str, object]]) -> Path:
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump({"projects": projects}, sort_keys=False), encoding="utf-8")
    return path


def _service_for(config_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectService:
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / "gaia.db"))
    settings = load_settings(config_path)
    database = Database(settings.database_path)
    return ProjectService(settings, database)


def _close_service(service: ProjectService) -> None:
    service.database.close()


def _capture_health(service: ProjectService, project_id: str) -> ProjectHealthSnapshot:
    return service.project_health(project_id)


def _recompute_health_fingerprint(snapshot: ProjectHealthSnapshot) -> str:
    payload = json.dumps(
        {
            "project_id": snapshot.project_id,
            "project_configuration_fingerprint": snapshot.project_configuration_fingerprint,
            "normalized_status": snapshot.normalized_status,
            "reason_codes": snapshot.reason_codes,
            "explanations": snapshot.explanations,
            "blocking_conditions": snapshot.blocking_conditions,
            "attention_conditions": snapshot.attention_conditions,
            "unknown_fields": snapshot.unknown_fields,
            "evidence_references": [item.model_dump(mode="json") for item in snapshot.evidence_references],
            "normalized_payload": snapshot.normalized_payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_identical_snapshots_are_noise_free(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        first = _capture_health(service, "sample")
        second = _capture_health(service, "sample")
        comparison = service.compare_project_health_snapshots(first.snapshot_id, second.snapshot_id)
        assert comparison.meaningful_change_detected is False
        assert comparison.finding_count == 0
        assert service.list_project_change_findings("sample") == []
    finally:
        _close_service(service)


def test_timestamp_only_difference_is_noise_free(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        original = _capture_health(service, "sample")
        duplicate = original.model_copy(
            update={
                "snapshot_id": "timestamp-only",
                "capture_timestamp": original.capture_timestamp + timedelta(seconds=5),
                "audit_event_id": "audit-different",
            }
        )
        service.database.insert_project_health_snapshot(duplicate)
        comparison = service.compare_project_health_snapshots(original.snapshot_id, duplicate.snapshot_id)
        assert comparison.meaningful_change_detected is False
        assert comparison.finding_count == 0
    finally:
        _close_service(service)


def test_working_tree_and_health_transition_are_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        clean = _capture_health(service, "sample")
        (repo / "README.md").write_text("# Project\nchanged\n", encoding="utf-8")
        dirty = _capture_health(service, "sample")
        comparison = service.compare_project_health_snapshots(clean.snapshot_id, dirty.snapshot_id)
        classes = {finding.change_class for finding in service.list_project_change_findings("sample")}
        assert comparison.meaningful_change_detected is True
        assert "health_transition" in classes
        assert "working_tree_change" in classes
    finally:
        _close_service(service)


def test_branch_head_and_detached_head_drift_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        base = _capture_health(service, "sample")
        subprocess.run(["git", "switch", "-c", "feature/change-intel"], cwd=repo, check=True, capture_output=True)
        (repo / "docs" / "status.md").write_text("Branch update.\n", encoding="utf-8")
        subprocess.run(["git", "add", "docs/status.md"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "branch move"], cwd=repo, check=True, capture_output=True)
        branch = _capture_health(service, "sample")
        comparison = service.compare_project_health_snapshots(base.snapshot_id, branch.snapshot_id)
        classes = {finding.change_class for finding in service.list_project_change_findings("sample")}
        assert comparison.meaningful_change_detected is True
        assert "branch_change" in classes
        assert "head_change" in classes

        subprocess.run(["git", "switch", "--detach", "HEAD"], cwd=repo, check=True, capture_output=True)
        detached = _capture_health(service, "sample")
        detached_comparison = service.compare_project_health_snapshots(branch.snapshot_id, detached.snapshot_id)
        detached_classes = {finding.change_class for finding in service.list_project_change_findings("sample")}
        assert detached_comparison.meaningful_change_detected is True
        assert "branch_change" in detached_classes
    finally:
        _close_service(service)


def test_upstream_divergence_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    peer = tmp_path / "peer"
    subprocess.run(["git", "clone", str(tmp_path / "repo.git"), str(peer)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=peer, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=peer, check=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        base = _capture_health(service, "sample")
        (peer / "extra.md").write_text("peer change\n", encoding="utf-8")
        subprocess.run(["git", "add", "extra.md"], cwd=peer, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "peer advance"], cwd=peer, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=peer, check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin"], cwd=repo, check=True, capture_output=True)
        behind = _capture_health(service, "sample")
        service.compare_project_health_snapshots(base.snapshot_id, behind.snapshot_id)
        classes = {finding.change_class for finding in service.list_project_change_findings("sample")}
        assert "upstream_divergence" in classes
    finally:
        _close_service(service)


def test_important_path_and_configuration_drift_are_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        first = _capture_health(service, "sample")
        (repo / "README.md").unlink()
        missing = _capture_health(service, "sample")
        service.compare_project_health_snapshots(first.snapshot_id, missing.snapshot_id)
        classes = {finding.change_class for finding in service.list_project_change_findings("sample")}
        assert "important_path_change" in classes

        (repo / "README.md").write_text("# Project\nrestored\n", encoding="utf-8")
        restored = _capture_health(service, "sample")
        service.compare_project_health_snapshots(missing.snapshot_id, restored.snapshot_id)
        restored_classes = {finding.change_class for finding in service.list_project_change_findings("sample")}
        assert "important_path_change" in restored_classes

        config_drift = first.model_copy(
            update={
                "snapshot_id": "config-drift",
                "project_configuration_fingerprint": "different-config",
            }
        )
        config_drift.content_fingerprint = _recompute_health_fingerprint(config_drift)
        service.database.insert_project_health_snapshot(config_drift)
        comparison = service.compare_project_health_snapshots(first.snapshot_id, config_drift.snapshot_id)
        classes = {finding.change_class for finding in service.list_project_change_findings("sample")}
        assert comparison.meaningful_change_detected is True
        assert "configuration_change" in classes
    finally:
        _close_service(service)


def test_stale_evidence_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        fresh = _capture_health(service, "sample")
        snapshot = service.snapshot("sample")
        stale_snapshot = snapshot.model_copy(update={"created_at": snapshot.created_at - timedelta(days=3)})
        service.database.insert_snapshot(stale_snapshot)
        stale = _capture_health(service, "sample")
        comparison = service.compare_project_health_snapshots(fresh.snapshot_id, stale.snapshot_id)
        classes = {finding.change_class for finding in service.list_project_change_findings("sample")}
        assert comparison.meaningful_change_detected is True
        assert "evidence_freshness_change" in classes
    finally:
        _close_service(service)


def test_cross_project_comparison_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_a = _init_repo(tmp_path / "repo-a", with_remote=True)
    repo_b = _init_repo(tmp_path / "repo-b", with_remote=True)
    service = _service_for(
        _write_settings(
            tmp_path,
            {
                "alpha": _project_config(repo_a, name="Alpha"),
                "beta": _project_config(repo_b, name="Beta"),
            },
        ),
        tmp_path,
        monkeypatch,
    )
    try:
        alpha = _capture_health(service, "alpha")
        beta = _capture_health(service, "beta")
        with pytest.raises(ValueError, match="Cross-project snapshot comparison is not allowed"):
            service.compare_project_health_snapshots(alpha.snapshot_id, beta.snapshot_id)
    finally:
        _close_service(service)


def test_schema_incompatibility_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        first = _capture_health(service, "sample")
        incompatible = first.model_copy(update={"snapshot_id": "v2", "schema_version": 2})
        service.database.insert_project_health_snapshot(incompatible)
        with pytest.raises(ValueError, match="Unsupported project-health schema version"):
            service.compare_project_health_snapshots(first.snapshot_id, incompatible.snapshot_id)
    finally:
        _close_service(service)


def test_stored_comparison_schema_incompatibility_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    service = _service_for(_write_settings(tmp_path, {"sample": _project_config(repo)}), tmp_path, monkeypatch)
    try:
        first = _capture_health(service, "sample")
        (repo / "README.md").write_text("# Project\nchanged\n", encoding="utf-8")
        dirty = _capture_health(service, "sample")
        comparison = service.compare_project_health_snapshots(first.snapshot_id, dirty.snapshot_id)
        payload = json.loads(comparison.model_dump_json())
        payload["schema_version"] = 2
        service.database.connection.execute(
            "UPDATE project_change_comparisons SET schema_version = ?, normalized_payload_json = ? WHERE comparison_id = ?",
            (2, json.dumps(payload, sort_keys=True, default=str), comparison.comparison_id),
        )
        service.database.connection.commit()
        with pytest.raises(ValueError, match="Unsupported project-change schema version"):
            service.get_project_change_comparison(comparison.comparison_id)
    finally:
        _close_service(service)


def test_portfolio_change_view_summarises_latest_meaningful_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path / "repo", with_remote=True)
    other = _init_repo(tmp_path / "other", with_remote=True)
    service = _service_for(
        _write_settings(
            tmp_path,
            {"sample": _project_config(repo), "other": _project_config(other)},
        ),
        tmp_path,
        monkeypatch,
    )
    try:
        clean = _capture_health(service, "sample")
        (repo / "README.md").write_text("# Project\nchanged\n", encoding="utf-8")
        dirty = _capture_health(service, "sample")
        service.compare_project_health_snapshots(clean.snapshot_id, dirty.snapshot_id)
        portfolio = service.project_change_portfolio()
        sample_entry = next(entry for entry in portfolio.projects if entry.project_id == "sample")
        assert sample_entry.latest_health_status == "attention"
        assert sample_entry.latest_findings
        assert portfolio.counts_by_severity["medium"] >= 1
    finally:
        _close_service(service)
