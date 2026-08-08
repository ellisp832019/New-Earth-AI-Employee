from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

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


def _write_settings(tmp_path: Path, projects: dict[str, dict[str, object]]) -> Path:
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump({"projects": projects}, sort_keys=False), encoding="utf-8")
    return path


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


def _service_for(
    config_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    db_name: str = "gaia.db",
) -> tuple[ProjectService, Database]:
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / db_name))
    settings = load_settings(config_path)
    database = Database(settings.database_path)
    return ProjectService(settings, database), database


def _project_entity_id(project_id: str) -> str:
    return f"architecture-entity:project:{project_id}"


def _shared_graph(service: ProjectService) -> None:
    shared_library = ArchitectureEntityContent(
        identity_key="shared-lib",
        kind="package",
        name="Shared Library",
        owning_project_or_domain="shared",
        repository=str(service.settings.projects["shared"].root),
        source_reference="docs/shared-lib.md",
        status="approved",
        freshness_state="fresh",
        provenance=ProgrammeProvenanceRecord(source_project_id="shared", repository=str(service.settings.projects["shared"].root)),
    )
    service.architecture_registry_service.create_entity_revision(shared_library, status="approved")

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
        "alpha",
        additional_content={"dependencies": ["shared-lib"]},
        status="approved",
    )
    service.project_contract_service.create_contract_for_project(
        "beta",
        additional_content={"dependencies": ["shared-lib"]},
        status="approved",
    )


def _build_cycle(service: ProjectService) -> None:
    service.architecture_registry_service.create_entity_revision(
        ArchitectureEntityContent(
            identity_key="cycle-a",
            kind="service",
            name="Cycle A",
            owning_project_or_domain="shared",
            repository=str(service.settings.projects["shared"].root),
            source_reference="docs/cycle-a.md",
            status="approved",
            freshness_state="fresh",
            provenance=ProgrammeProvenanceRecord(source_project_id="shared", repository=str(service.settings.projects["shared"].root)),
        ),
        status="approved",
    )
    service.architecture_registry_service.create_entity_revision(
        ArchitectureEntityContent(
            identity_key="cycle-b",
            kind="service",
            name="Cycle B",
            owning_project_or_domain="shared",
            repository=str(service.settings.projects["shared"].root),
            source_reference="docs/cycle-b.md",
            status="approved",
            freshness_state="fresh",
            provenance=ProgrammeProvenanceRecord(source_project_id="shared", repository=str(service.settings.projects["shared"].root)),
        ),
        status="approved",
    )
    service.architecture_registry_service.create_relationship_revision(
        ArchitectureRelationshipContent(
            identity_key="cycle-a-to-b",
            relationship_type="DEPENDS_ON",
            source_entity_id="architecture-entity:service:cycle-a",
            target_entity_id="architecture-entity:service:cycle-b",
            status="approved",
            freshness_state="fresh",
            provenance=ProgrammeProvenanceRecord(source_project_id="shared", repository=str(service.settings.projects["shared"].root)),
        ),
        status="approved",
    )
    service.architecture_registry_service.create_relationship_revision(
        ArchitectureRelationshipContent(
            identity_key="cycle-b-to-a",
            relationship_type="DEPENDS_ON",
            source_entity_id="architecture-entity:service:cycle-b",
            target_entity_id="architecture-entity:service:cycle-a",
            status="approved",
            freshness_state="fresh",
            provenance=ProgrammeProvenanceRecord(source_project_id="shared", repository=str(service.settings.projects["shared"].root)),
        ),
        status="approved",
    )
    service.project_contract_service.create_contract_for_project(
        "shared",
        additional_content={"dependencies": ["missing-lib"]},
        status="approved",
    )


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


def test_dependency_graph_is_deterministic_across_insertion_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _build_settings(tmp_path)
    service_a, database_a = _service_for(config, tmp_path, monkeypatch, db_name="graph-a.db")
    try:
        _shared_graph(service_a)
        graph_a = service_a.dependency_graph()
        alpha_dependencies_a = service_a.project_dependency_graph("alpha")
        shared_dependencies_a = service_a.dependency_graph_shared_dependencies()
        orphan_ids_a = [item.orphan_id for item in service_a.dependency_graph_orphans()]
    finally:
        database_a.close()

    service_b, database_b = _service_for(config, tmp_path, monkeypatch, db_name="graph-b.db")
    try:
        service_b.project_contract_service.create_contract_for_project(
            "beta",
            additional_content={"dependencies": ["shared-lib"]},
            status="approved",
        )
        service_b.project_contract_service.create_contract_for_project(
            "alpha",
            additional_content={"dependencies": ["shared-lib"]},
            status="approved",
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
        graph_b = service_b.dependency_graph()
        assert graph_a.graph_fingerprint == graph_b.graph_fingerprint
        assert [node.node_id for node in graph_a.nodes] == [node.node_id for node in graph_b.nodes]
        assert [edge.edge_id for edge in graph_a.edges] == [edge.edge_id for edge in graph_b.edges]
        assert [finding.finding_id for finding in graph_a.findings] == [finding.finding_id for finding in graph_b.findings]
        assert [item.target_project_id for item in alpha_dependencies_a] == ["shared"]
        assert [item.target_project_id for item in service_b.project_dependency_graph("alpha")] == ["shared"]
        assert [item.dependent_project_ids for item in shared_dependencies_a] == [["alpha", "beta"]]
        assert orphan_ids_a == []
    finally:
        database_b.close()


def test_dependency_graph_cycles_and_unresolved_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _build_settings(tmp_path)
    service, database = _service_for(config, tmp_path, monkeypatch, db_name="graph-cycles.db")
    try:
        _build_cycle(service)
        cycles = service.dependency_graph_cycles()
        unresolved = service.dependency_graph_findings()
        alpha_dependencies = service.dependency_graph_dependency(_project_entity_id("shared"), transitive=True)
        assert len(cycles) == 1
        assert cycles[0].node_ids == sorted(cycles[0].node_ids)
        assert cycles[0].edge_ids == sorted(cycles[0].edge_ids)
        assert any(finding.finding_type == "unresolved_dependency" for finding in unresolved)
        assert all(record.node_id != _project_entity_id("shared") for record in alpha_dependencies)
    finally:
        database.close()


def test_dependency_graph_rebuilds_identically_after_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _build_settings(tmp_path)
    service, database = _service_for(config, tmp_path, monkeypatch, db_name="graph-restart.db")
    try:
        _shared_graph(service)
        graph_before = service.dependency_graph()
    finally:
        database.close()

    service, database = _service_for(config, tmp_path, monkeypatch, db_name="graph-restart.db")
    try:
        graph_after = service.dependency_graph()
        assert graph_before.graph_fingerprint == graph_after.graph_fingerprint
        assert [node.node_id for node in graph_before.nodes] == [node.node_id for node in graph_after.nodes]
        assert [edge.edge_id for edge in graph_before.edges] == [edge.edge_id for edge in graph_after.edges]
    finally:
        database.close()
