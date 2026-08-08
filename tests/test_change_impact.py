from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from gaia.change_impact import ChangeProposal, ChangeProposalTarget
from gaia.config import load_settings
from gaia.db import Database
from gaia.models import WorkPackageRecord
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


def _project_settings(repo: Path) -> dict[str, object]:
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


def _build_settings(tmp_path: Path) -> Path:
    alpha = _init_repo(tmp_path / "alpha")
    beta = _init_repo(tmp_path / "beta")
    shared = _init_repo(tmp_path / "shared")
    return _write_settings(
        tmp_path,
        {
            "alpha": _project_settings(alpha),
            "beta": _project_settings(beta),
            "shared": _project_settings(shared),
        },
    )


def _bootstrap_graph(service: ProjectService, *, shared_contract_changes: dict[str, object] | None = None) -> None:
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
    service.architecture_registry_service.create_relationship_revision(
        ArchitectureRelationshipContent(
            identity_key="alpha-shared-lib",
            relationship_type="DEPENDS_ON",
            source_entity_id=_project_entity_id("alpha"),
            target_entity_id="architecture-entity:package:shared-lib",
            status="approved",
            freshness_state="fresh",
            provenance=ProgrammeProvenanceRecord(source_project_id="alpha", repository=str(service.settings.projects["alpha"].root)),
        ),
        status="approved",
    )
    service.architecture_registry_service.create_relationship_revision(
        ArchitectureRelationshipContent(
            identity_key="beta-shared-lib",
            relationship_type="DEPENDS_ON",
            source_entity_id=_project_entity_id("beta"),
            target_entity_id="architecture-entity:package:shared-lib",
            status="approved",
            freshness_state="fresh",
            provenance=ProgrammeProvenanceRecord(source_project_id="beta", repository=str(service.settings.projects["beta"].root)),
        ),
        status="approved",
    )
    service.project_contract_service.create_contract_for_project(
        "shared",
        status="approved",
        additional_content={
            "test_commands": [r".\.venv\Scripts\python.exe -m pytest"],
            "build_commands": [r".\.venv\Scripts\python.exe -m build"],
            "documentation_roots": ["docs", "README.md"],
            "release_process_reference": "docs/release.md",
            "version": "1.0.0",
            **(shared_contract_changes or {}),
        },
    )


def test_change_impact_is_deterministic_across_insertion_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _build_settings(tmp_path)
    service_a, database_a = _service_for(config, tmp_path, monkeypatch, db_name="impact-a.db")
    try:
        _bootstrap_graph(service_a)
        result_a = service_a.analyse_change_proposal(
            ChangeProposal(
                title="Update shared library",
                origin_project="shared",
                objective="Change the shared library contract.",
                change_type="SHARED_LIBRARY_CHANGE",
                target_entities=[ChangeProposalTarget(target_kind="architecture_entity", target_id="architecture-entity:package:shared-lib")],
            )
        )
    finally:
        database_a.close()

    service_b, database_b = _service_for(config, tmp_path, monkeypatch, db_name="impact-b.db")
    try:
        service_b.project_contract_service.create_contract_for_project(
            "shared",
            status="approved",
            additional_content={
                "release_process_reference": "docs/release.md",
                "documentation_roots": ["docs", "README.md"],
                "build_commands": [r".\.venv\Scripts\python.exe -m build"],
                "test_commands": [r".\.venv\Scripts\python.exe -m pytest"],
                "version": "1.0.0",
            },
        )
        service_b.architecture_registry_service.create_entity_revision(
            ArchitectureEntityContent(
                identity_key="shared-lib",
                kind="package",
                name="Shared Library",
                owning_project_or_domain="shared",
                repository=str(service_b.settings.projects["shared"].root),
                source_reference="docs/shared-lib.md",
                status="approved",
                freshness_state="fresh",
                provenance=ProgrammeProvenanceRecord(source_project_id="shared", repository=str(service_b.settings.projects["shared"].root)),
            ),
            status="approved",
        )
        service_b.architecture_registry_service.create_relationship_revision(
            ArchitectureRelationshipContent(
                identity_key="beta-shared-lib",
                relationship_type="DEPENDS_ON",
                source_entity_id=_project_entity_id("beta"),
                target_entity_id="architecture-entity:package:shared-lib",
                status="approved",
                freshness_state="fresh",
                provenance=ProgrammeProvenanceRecord(source_project_id="beta", repository=str(service_b.settings.projects["beta"].root)),
            ),
            status="approved",
        )
        service_b.architecture_registry_service.create_relationship_revision(
            ArchitectureRelationshipContent(
                identity_key="alpha-shared-lib",
                relationship_type="DEPENDS_ON",
                source_entity_id=_project_entity_id("alpha"),
                target_entity_id="architecture-entity:package:shared-lib",
                status="approved",
                freshness_state="fresh",
                provenance=ProgrammeProvenanceRecord(source_project_id="alpha", repository=str(service_b.settings.projects["alpha"].root)),
            ),
            status="approved",
        )
        result_b = service_b.analyse_change_proposal(
            ChangeProposal(
                title="Update shared library",
                origin_project="shared",
                objective="Change the shared library contract.",
                change_type="SHARED_LIBRARY_CHANGE",
                target_entities=[ChangeProposalTarget(target_kind="architecture_entity", target_id="architecture-entity:package:shared-lib")],
            )
        )
        assert result_a.impact_fingerprint == result_b.impact_fingerprint
        assert [item.project_id for item in result_a.affected_projects] == [item.project_id for item in result_b.affected_projects]
        assert [item.reference for item in result_a.validation_references] == [item.reference for item in result_b.validation_references]
    finally:
        database_b.close()


def test_change_impact_preview_contract_change_and_work_package_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _build_settings(tmp_path)
    service, database = _service_for(config, tmp_path, monkeypatch, db_name="impact-contract.db")
    try:
        _bootstrap_graph(service)
        database.insert_work_package(
            WorkPackageRecord(
                project_id="alpha",
                title="Alpha package",
                objective="Review alpha change impact.",
            )
        )
        result = service.analyse_change_proposal(
            ChangeProposal(
                title="Project shared contract update",
                origin_project="shared",
                objective="Add a new shared-lib dependency and bump the version.",
                change_type="PROJECT_CONTRACT_CHANGE",
                target_entities=[ChangeProposalTarget(target_kind="project_contract", target_id="shared")],
                proposed_contract_changes={"dependencies": ["shared-lib"], "version": "2.0.0"},
            )
        )
        assert any(item.project_id == "shared" for item in result.affected_contracts)
        assert any(item.project_id == "shared" for item in result.affected_releases)
        assert any(item.project_id == "alpha" for item in result.affected_work_packages)
        assert any(item.reference_kind == "test_command" for item in result.validation_references)
        assert any(item.dependent_project_id == "alpha" for item in result.sequencing_constraints)
        assert result.risk.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    finally:
        database.close()


def test_change_impact_unknown_target_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _build_settings(tmp_path)
    service, database = _service_for(config, tmp_path, monkeypatch, db_name="impact-unknown.db")
    try:
        _bootstrap_graph(service)
        result = service.analyse_change_proposal(
            ChangeProposal(
                title="Unknown target",
                origin_project="shared",
                objective="Probe an unresolved target.",
                change_type="API_CHANGE",
                target_entities=[ChangeProposalTarget(target_kind="architecture_entity", target_id="architecture-entity:package:missing")],
            )
        )
        assert any(finding.finding_type == "UNKNOWN_TARGET" for finding in result.unknown_findings)
        assert result.risk.risk_level != "LOW"
        assert any(requirement.reason_code == "UNKNOWN_TARGET" for requirement in result.refresh_requirements)
    finally:
        database.close()
