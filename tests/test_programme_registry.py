from __future__ import annotations

import sqlite3
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


def _service_for(config_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ProjectService, Database]:
    monkeypatch.setenv("GAIA_DATABASE_PATH", str(tmp_path / "gaia.db"))
    settings = load_settings(config_path)
    database = Database(settings.database_path)
    return ProjectService(settings, database), database


def test_contract_bootstrap_and_revision_deduplication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "project")
    config = _write_settings(tmp_path, {"project": _project_settings(repo)})
    service, database = _service_for(config, tmp_path, monkeypatch)
    try:
        contract = service.current_project_contract("project")
        assert contract is not None
        assert contract.project_id == "project"
        assert contract.status == "approved"
        assert contract.current_revision is not None
        assert contract.current_revision.content.project_id == "project"

        revisions = service.project_contract_revisions("project")
        assert len(revisions) == 1
        duplicate = service.project_contract_service.create_contract_for_project("project", status="approved")
        assert duplicate.revision_id == revisions[0].revision_id
        assert len(service.project_contract_revisions("project")) == 1
    finally:
        database.close()


def test_architecture_registry_bootstrap_and_relationship_filters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "project")
    config = _write_settings(tmp_path, {"project": _project_settings(repo)})
    service, database = _service_for(config, tmp_path, monkeypatch)
    try:
        entities = service.architecture_entities(project_id="project")
        assert [entity.kind for entity in entities] == ["project"]
        project_entity = entities[0]
        assert project_entity.identity_key == "project"
        assert project_entity.status == "approved"

        package_content = ArchitectureEntityContent(
            identity_key="project-package",
            kind="package",
            name="Project Package",
            owning_project_or_domain="project",
            repository=str(repo),
            source_reference="README.md",
            status="approved",
            provenance=ProgrammeProvenanceRecord(source_project_id="project", repository=str(repo)),
        )
        package_revision = service.architecture_registry_service.create_entity_revision(package_content, status="approved")
        package_entity = service.architecture_entity(package_revision.entity_id)
        assert package_entity is not None
        assert package_entity.kind == "package"

        duplicate = service.architecture_registry_service.create_entity_revision(package_content, status="approved")
        assert duplicate.revision_id == package_revision.revision_id
        assert len(service.architecture_registry_service.list_entity_revisions(package_revision.entity_id)) == 1

        relationship_content = ArchitectureRelationshipContent(
            identity_key="project-depends-on-package",
            relationship_type="DEPENDS_ON",
            source_entity_id=project_entity.entity_id,
            target_entity_id=package_entity.entity_id,
            status="approved",
            provenance=ProgrammeProvenanceRecord(source_project_id="project", repository=str(repo)),
        )
        relationship_revision = service.architecture_registry_service.create_relationship_revision(
            relationship_content,
            status="approved",
        )
        assert relationship_revision.identity_key == "project-depends-on-package"
        assert service.architecture_relationship(relationship_revision.relationship_id) is not None
        assert service.architecture_relationships(source_entity_id=project_entity.entity_id)[0].relationship_id == relationship_revision.relationship_id
        assert service.architecture_relationships(relationship_type="DEPENDS_ON")[0].relationship_id == relationship_revision.relationship_id
    finally:
        database.close()


def test_architecture_registry_bootstrap_can_reopen_existing_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "project")
    config = _write_settings(tmp_path, {"project": _project_settings(repo)})

    first_service, first_database = _service_for(config, tmp_path, monkeypatch)
    try:
        first_entities = first_service.architecture_entities(project_id="project")
        assert len(first_entities) == 1
        first_entity_id = first_entities[0].entity_id
    finally:
        first_database.close()

    second_service, second_database = _service_for(config, tmp_path, monkeypatch)
    try:
        second_entities = second_service.architecture_entities(project_id="project")
        assert [entity.entity_id for entity in second_entities] == [first_entity_id]
        assert second_entities[0].current_revision_id is not None
        assert len(second_service.architecture_registry_service.list_entity_revisions(first_entity_id)) >= 1
    finally:
        second_database.close()


def test_registry_validation_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path / "project")
    config = _write_settings(tmp_path, {"project": _project_settings(repo)})
    service, database = _service_for(config, tmp_path, monkeypatch)
    try:
        with pytest.raises(KeyError):
            service.project_contract_service.create_contract_for_project("missing")

        with pytest.raises(KeyError):
            service.architecture_registry_service.create_entity_revision(
                ArchitectureEntityContent(
                    identity_key="missing",
                    kind="project",
                    name="Missing Project",
                    owning_project_or_domain="missing",
                    repository=str(repo),
                    source_reference="README.md",
                    status="approved",
                ),
                status="approved",
            )

        project_entity = service.architecture_entities(project_id="project")[0]
        with pytest.raises(KeyError):
            service.architecture_registry_service.create_relationship_revision(
                ArchitectureRelationshipContent(
                    identity_key="invalid-relationship",
                    relationship_type="DEPENDS_ON",
                    source_entity_id=project_entity.entity_id,
                    target_entity_id="architecture-entity:package:missing",
                    status="approved",
                    provenance=ProgrammeProvenanceRecord(source_project_id="project", repository=str(repo)),
                ),
                status="approved",
            )
    finally:
        database.close()


def test_schema_migrates_from_version_eleven_and_preserves_documents(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE documents (project_id TEXT NOT NULL, relative_path TEXT NOT NULL, extension TEXT NOT NULL, size_bytes INTEGER NOT NULL, modified_utc TEXT NOT NULL, sha256 TEXT NOT NULL, tracked INTEGER, indexing_status TEXT NOT NULL, warning TEXT, scanned_at TEXT NOT NULL, content TEXT, PRIMARY KEY(project_id, relative_path))"
    )
    connection.execute(
        "INSERT INTO documents(project_id, relative_path, extension, size_bytes, modified_utc, sha256, tracked, indexing_status, warning, scanned_at, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("sample", "README.md", ".md", 10, "2026-08-05T00:00:00+00:00", "abc", 1, "indexed", None, "2026-08-05T00:00:00+00:00", "hello"),
    )
    connection.execute("PRAGMA user_version = 11")
    connection.commit()
    connection.close()

    database = Database(db_path)
    try:
        assert database.connection.execute("PRAGMA user_version").fetchone()[0] == 13
        row = database.connection.execute("SELECT relative_path FROM documents").fetchone()
        assert row[0] == "README.md"
        assert database.connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_contracts'").fetchone() is not None
        assert database.connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='architecture_entities'").fetchone() is not None
    finally:
        database.close()
