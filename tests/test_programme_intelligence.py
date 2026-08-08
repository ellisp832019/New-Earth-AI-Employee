from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from gaia.change_impact import ChangeImpactResult, ChangeProposal, ChangeProposalTarget
from gaia.config import load_settings
from gaia.db import Database
from gaia.programme_registry import (
    ArchitectureEntityContent,
    ArchitectureRelationshipContent,
    ProgrammeProvenanceRecord,
)
from gaia.service import ProjectService


def _init_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("# Project\n", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "status.md").write_text("Initial status.\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", "docs/status.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    return repo


def _project_settings(repo: Path, *, important_paths: list[str] | None = None) -> dict[str, object]:
    return {
        "name": repo.name,
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
        "important_paths": important_paths or ["README.md", "docs"],
        "health_rules": {"evidence_freshness_hours": 24, "required_paths": ["README.md", "docs"]},
        "release_rules": {"assume_unknown_when_no_upstream": True},
        "approval_requirements": {"registry_review": "required"},
        "metadata": {"owner": repo.name},
    }


def _write_settings(tmp_path: Path, projects: dict[str, dict[str, object]]) -> Path:
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump({"projects": projects}, sort_keys=False), encoding="utf-8")
    return path


def _service_for(
    config_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    db_name: str,
) -> tuple[ProjectService, Database]:
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / db_name))
    settings = load_settings(config_path)
    database = Database(settings.database_path)
    return ProjectService(settings, database), database


def _project_entity_id(project_id: str) -> str:
    return f"architecture-entity:project:{project_id}"


def _build_settings(tmp_path: Path, *, alpha_missing_path: bool) -> Path:
    alpha = _init_repo(tmp_path / "alpha")
    beta = _init_repo(tmp_path / "beta")
    shared = _init_repo(tmp_path / "shared")
    alpha_paths = ["README.md", "missing.txt"] if alpha_missing_path else ["README.md", "docs"]
    return _write_settings(
        tmp_path,
        {
            "alpha": _project_settings(alpha, important_paths=alpha_paths),
            "beta": _project_settings(beta),
            "shared": _project_settings(shared),
        },
    )


def _seed_release_graph(service: ProjectService, *, relationship_order: list[str]) -> None:
    service.architecture_registry_service.create_entity_revision(
        ArchitectureEntityContent(
            identity_key="shared-lib",
            kind="package",
            name="Shared Library",
            owning_project_or_domain="shared",
            repository=str(service.settings.projects["shared"].root),
            source_reference="docs/shared-lib.md",
            status="approved",
            freshness_state="fresh",
            provenance=ProgrammeProvenanceRecord(source_project_id="shared", repository=str(service.settings.projects["shared"].root)),
        ),
        status="approved",
    )
    for project_id in relationship_order:
        service.architecture_registry_service.create_relationship_revision(
            ArchitectureRelationshipContent(
                identity_key=f"{project_id}-shared-lib",
                relationship_type="DEPENDS_ON",
                source_entity_id=_project_entity_id(project_id),
                target_entity_id="architecture-entity:package:shared-lib",
                status="approved",
                freshness_state="fresh",
                provenance=ProgrammeProvenanceRecord(source_project_id=project_id, repository=str(service.settings.projects[project_id].root)),
            ),
            status="approved",
        )
    for project_id, version in {"shared": "1.0.0", "alpha": "1.0.0", "beta": "1.1.0"}.items():
        service.project_contract_service.create_contract_for_project(
            project_id,
            status="approved",
            additional_content={
                "release_process_reference": "docs/release.md",
                "documentation_roots": ["docs", "README.md"],
                "build_commands": [r".\.venv\Scripts\python.exe -m build"],
                "test_commands": [r".\.venv\Scripts\python.exe -m pytest"],
                "version": version,
                "dependencies": ["shared-lib"] if project_id in {"alpha", "beta"} else [],
            },
        )
    for project_id in ("alpha", "beta", "shared"):
        service.project_health(project_id)


def _analyse_shared_contract_change(service: ProjectService) -> ChangeImpactResult:
    return service.analyse_change_proposal(
        ChangeProposal(
            title="Project shared contract update",
            origin_project="shared",
            objective="Add a new shared-lib dependency and bump the version.",
            change_type="PROJECT_CONTRACT_CHANGE",
            target_entities=[ChangeProposalTarget(target_kind="project_contract", target_id="shared")],
            proposed_contract_changes={"dependencies": ["shared-lib"], "version": "2.0.0"},
        )
    )


def test_programme_roadmap_is_deterministic_across_insertion_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _build_settings(tmp_path, alpha_missing_path=True)
    service_a, database_a = _service_for(config, tmp_path, monkeypatch, db_name="roadmap-a.db")
    try:
        _seed_release_graph(service_a, relationship_order=["alpha", "beta"])
        impact_a = _analyse_shared_contract_change(service_a)
        roadmap_a = service_a.programme_roadmap(change_impact_results=[impact_a])
    finally:
        database_a.close()

    service_b, database_b = _service_for(config, tmp_path, monkeypatch, db_name="roadmap-b.db")
    try:
        _seed_release_graph(service_b, relationship_order=["beta", "alpha"])
        impact_b = _analyse_shared_contract_change(service_b)
        roadmap_b = service_b.programme_roadmap(change_impact_results=[impact_b])
    finally:
        database_b.close()

    assert roadmap_a.roadmap_fingerprint == roadmap_b.roadmap_fingerprint
    assert [item.roadmap_item_id for item in roadmap_a.roadmap_items] == [
        item.roadmap_item_id for item in roadmap_b.roadmap_items
    ]
    assert [item.roadmap_state for item in roadmap_a.roadmap_items] == [
        item.roadmap_state for item in roadmap_b.roadmap_items
    ]
    assert any(item.source_type == "project_blocker" for item in roadmap_a.roadmap_items)
    assert any(item.source_type == "change_impact" for item in roadmap_a.roadmap_items)
    assert any(item.roadmap_state == "NOW" for item in roadmap_a.roadmap_items)
    assert any(item.roadmap_state == "WAITING_FOR_EVIDENCE" for item in roadmap_a.roadmap_items)


def test_release_trains_discover_dependency_order_and_requirements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _build_settings(tmp_path, alpha_missing_path=False)
    service_a, database_a = _service_for(config, tmp_path, monkeypatch, db_name="train-a.db")
    try:
        _seed_release_graph(service_a, relationship_order=["alpha", "beta"])
        impact_a = _analyse_shared_contract_change(service_a)
        portfolio_a = service_a.release_trains(change_impact_results=[impact_a])
    finally:
        database_a.close()

    service_b, database_b = _service_for(config, tmp_path, monkeypatch, db_name="train-b.db")
    try:
        _seed_release_graph(service_b, relationship_order=["beta", "alpha"])
        impact_b = _analyse_shared_contract_change(service_b)
        portfolio_b = service_b.release_trains(change_impact_results=[impact_b])
    finally:
        database_b.close()

    assert portfolio_a.release_train_fingerprint == portfolio_b.release_train_fingerprint
    assert len(portfolio_a.release_trains) == 1
    train = portfolio_a.release_trains[0]
    assert train.dependency_order[0] == "shared"
    assert set(train.dependency_order) == {"shared", "alpha", "beta"}
    assert [participant.project_id for participant in train.participating_projects] == train.dependency_order
    assert any(reference.reference_kind == "test_command" for reference in train.required_tests)
    assert train.release_readiness != "UNKNOWN"
