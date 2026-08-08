from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gaia.config import Settings
from gaia.models import ProjectConfig, ProjectHealthEvidenceReference, utc_now

if TYPE_CHECKING:
    from gaia.audit import AuditRecorder
    from gaia.db import Database

ProjectContractStatus = Literal["draft", "approved", "superseded", "retired"]
ProjectContractAuthorityLevel = Literal["read_only", "gaia_local_state", "manual_handoff_only", "unsupported"]
ProjectCriticality = Literal["low", "medium", "high", "critical", "unknown"]
ProjectRiskClass = Literal["low", "medium", "high", "critical", "unknown"]
EvidenceFreshnessState = Literal["fresh", "stale", "unknown", "unavailable"]

ArchitectureEntityKind = Literal[
    "project",
    "service",
    "api",
    "package",
    "library",
    "firmware",
    "hardware",
    "protocol",
    "database",
    "local_service",
    "user_interface",
    "integration_client",
    "schema",
    "release_contract",
]

ArchitectureEntityStatus = ProjectContractStatus

ArchitectureRelationshipType = Literal[
    "DEPENDS_ON",
    "PROVIDES_API_TO",
    "CONSUMES_API_FROM",
    "EMBEDS",
    "USES_PACKAGE",
    "PRODUCES_DATA_FOR",
    "CONSUMES_DATA_FROM",
    "CONTROLS",
    "MONITORS",
    "SHARES_SCHEMA_WITH",
    "RELEASES_WITH",
    "BLOCKS",
    "REPLACES",
    "SUPERSEDES",
    "VALIDATES",
    "DEPLOYED_WITH",
]
ArchitectureRelationshipStatus = ProjectContractStatus


class ProgrammeProvenanceRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_project_id: str | None = None
    repository: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    source_document: str | None = None
    captured_at: str = Field(default_factory=lambda: utc_now().isoformat())
    evidence_reference: str | None = None
    manual_operator_source: str | None = None
    canonical_gaia_source: str = "gaia"
    details: dict[str, Any] = Field(default_factory=dict)


class ProjectContractContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: str
    name: str
    repository: str
    project_type: str | None = None
    owner: str | None = None
    purpose: str | None = None
    status: ProjectContractStatus = "draft"
    authority_level: ProjectContractAuthorityLevel = "read_only"
    primary_technologies: list[str] = Field(default_factory=list)
    supported_platforms: list[str] = Field(default_factory=list)
    interfaces_exposed: list[str] = Field(default_factory=list)
    interfaces_consumed: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    shared_packages: list[str] = Field(default_factory=list)
    hardware_dependencies: list[str] = Field(default_factory=list)
    data_contracts: list[str] = Field(default_factory=list)
    api_contracts: list[str] = Field(default_factory=list)
    release_channel: str | None = None
    version: str | None = None
    criticality: ProjectCriticality = "unknown"
    risk_class: ProjectRiskClass = "unknown"
    documentation_roots: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)
    build_commands: list[str] = Field(default_factory=list)
    release_process_reference: str | None = None
    architecture_references: list[str] = Field(default_factory=list)
    known_constraints: list[str] = Field(default_factory=list)
    security_boundary: str | None = None
    evidence_freshness_policy: dict[str, Any] | None = None

    @field_validator(
        "primary_technologies",
        "supported_platforms",
        "interfaces_exposed",
        "interfaces_consumed",
        "dependencies",
        "shared_packages",
        "hardware_dependencies",
        "data_contracts",
        "api_contracts",
        "documentation_roots",
        "test_commands",
        "build_commands",
        "architecture_references",
        "known_constraints",
    )
    @classmethod
    def _normalise_lists(cls, values: list[str]) -> list[str]:
        return _normalise_strings(values)

    @field_validator("project_id", "name", "repository")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class ProjectContractRevisionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revision_id: str = Field(default_factory=lambda: str(uuid5(NAMESPACE_URL, "gaia:project-contract-revision")))
    contract_id: str
    project_id: str
    revision_number: int = Field(ge=1)
    previous_revision_id: str | None = None
    status: ProjectContractStatus = "draft"
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    created_by: str = "system"
    content: ProjectContractContent
    semantic_fingerprint: str = ""
    content_fingerprint: str = ""
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    evidence_references: list[ProjectHealthEvidenceReference] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    supersedes_revision_id: str | None = None
    normalized_payload: dict[str, Any] = Field(default_factory=dict)


class ProjectContractRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contract_id: str
    project_id: str
    current_revision_id: str | None = None
    current_revision_number: int = 0
    approved_revision_id: str | None = None
    approved_revision_number: int | None = None
    status: ProjectContractStatus = "draft"
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    content_fingerprint: str = ""
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    freshness_state: EvidenceFreshnessState = "unknown"
    current_revision: ProjectContractRevisionRecord | None = None
    normalized_payload: dict[str, Any] = Field(default_factory=dict)


class ArchitectureEntityContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    identity_key: str
    kind: ArchitectureEntityKind
    name: str
    owning_project_or_domain: str | None = None
    repository: str | None = None
    source_reference: str | None = None
    status: ArchitectureEntityStatus = "draft"
    freshness_state: EvidenceFreshnessState = "unknown"
    relationship_references: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)

    @field_validator("identity_key", "name")
    @classmethod
    def _identity_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("relationship_references", "notes")
    @classmethod
    def _normalise_lists(cls, values: list[str]) -> list[str]:
        return _normalise_strings(values)


class ArchitectureEntityRevisionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revision_id: str = Field(default_factory=lambda: str(uuid5(NAMESPACE_URL, "gaia:architecture-entity-revision")))
    entity_id: str
    identity_key: str
    revision_number: int = Field(ge=1)
    previous_revision_id: str | None = None
    status: ArchitectureEntityStatus = "draft"
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    created_by: str = "system"
    content: ArchitectureEntityContent
    semantic_fingerprint: str = ""
    content_fingerprint: str = ""
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    evidence_references: list[ProjectHealthEvidenceReference] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    supersedes_revision_id: str | None = None
    normalized_payload: dict[str, Any] = Field(default_factory=dict)


class ArchitectureEntityRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entity_id: str
    identity_key: str
    kind: ArchitectureEntityKind
    name: str
    owning_project_or_domain: str | None = None
    repository: str | None = None
    source_reference: str | None = None
    current_revision_id: str | None = None
    current_revision_number: int = 0
    status: ArchitectureEntityStatus = "draft"
    freshness_state: EvidenceFreshnessState = "unknown"
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    current_revision: ArchitectureEntityRevisionRecord | None = None
    content_fingerprint: str = ""
    normalized_payload: dict[str, Any] = Field(default_factory=dict)


class ArchitectureRelationshipContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    identity_key: str
    relationship_type: ArchitectureRelationshipType
    source_entity_id: str
    target_entity_id: str
    status: ArchitectureRelationshipStatus = "draft"
    freshness_state: EvidenceFreshnessState = "unknown"
    notes: list[str] = Field(default_factory=list)
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    evidence_references: list[ProjectHealthEvidenceReference] = Field(default_factory=list)

    @field_validator("identity_key", "source_entity_id", "target_entity_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("notes")
    @classmethod
    def _normalise_lists(cls, values: list[str]) -> list[str]:
        return _normalise_strings(values)


class ArchitectureRelationshipRevisionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revision_id: str = Field(default_factory=lambda: str(uuid5(NAMESPACE_URL, "gaia:architecture-relationship-revision")))
    relationship_id: str
    identity_key: str
    revision_number: int = Field(ge=1)
    previous_revision_id: str | None = None
    status: ArchitectureRelationshipStatus = "draft"
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    created_by: str = "system"
    content: ArchitectureRelationshipContent
    semantic_fingerprint: str = ""
    content_fingerprint: str = ""
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    evidence_references: list[ProjectHealthEvidenceReference] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    supersedes_revision_id: str | None = None
    normalized_payload: dict[str, Any] = Field(default_factory=dict)


class ArchitectureRelationshipRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    relationship_id: str
    identity_key: str
    relationship_type: ArchitectureRelationshipType
    source_entity_id: str
    target_entity_id: str
    current_revision_id: str | None = None
    current_revision_number: int = 0
    status: ArchitectureRelationshipStatus = "draft"
    freshness_state: EvidenceFreshnessState = "unknown"
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    current_revision: ArchitectureRelationshipRevisionRecord | None = None
    content_fingerprint: str = ""
    normalized_payload: dict[str, Any] = Field(default_factory=dict)


class ProjectContractService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        audit: AuditRecorder | None = None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.audit = audit

    def bootstrap_from_settings(self) -> list[ProjectContractRecord]:
        bootstrapped: list[ProjectContractRecord] = []
        for project in sorted(self.settings.projects.values(), key=lambda item: item.project_id):
            bootstrapped.append(self.ensure_project_contract(project))
        return bootstrapped

    def ensure_project_contract(self, project: ProjectConfig) -> ProjectContractRecord:
        content = self._content_from_project(project)
        revision = self.create_contract_revision(
            content,
            status="approved",
            created_by="bootstrap",
            provenance=self._provenance_for_project(project, source_document="config/projects.yaml"),
            freshness_state="fresh",
        )
        return self._current_contract(project.project_id) or self._contract_from_revision(revision)

    def create_contract_revision(
        self,
        content: ProjectContractContent,
        *,
        status: ProjectContractStatus = "draft",
        created_by: str = "system",
        provenance: ProgrammeProvenanceRecord | None = None,
        evidence_references: list[ProjectHealthEvidenceReference] | None = None,
        freshness_state: EvidenceFreshnessState = "unknown",
    ) -> ProjectContractRevisionRecord:
        self._validate_content(content)
        existing = self.database.get_project_contract_revision_by_semantic(content.project_id, _contract_semantic_fingerprint(content))
        if existing is not None:
            if status == "approved" and existing.status != "approved":
                return self.approve_contract_revision(existing.revision_id, approved_by=created_by).current_revision or existing
            return existing

        revision_number = self.database.next_project_contract_revision_number(content.project_id)
        contract_id = self._contract_id(content.project_id)
        previous = self.database.get_project_contract(content.project_id)
        provenance = provenance or self._provenance_for_content(content)
        if previous is None:
            self.database.upsert_project_contract(
                ProjectContractRecord(
                    contract_id=contract_id,
                    project_id=content.project_id,
                    current_revision_id=None,
                    current_revision_number=0,
                    approved_revision_id=None,
                    approved_revision_number=None,
                    status="draft",
                    provenance=provenance,
                    freshness_state=freshness_state,
                )
            )
        if self.audit is not None:
            event = self.audit.record(
                category="programme_registry",
                operation="create_project_contract_revision",
                project_id=content.project_id,
                outcome="success",
                metadata={"contract_id": contract_id, "revision_number": revision_number, "status": status},
            )
            provenance = provenance.model_copy(update={"details": {**provenance.details, "audit_event_id": event.event_id}})
        revision = ProjectContractRevisionRecord(
            revision_id=_deterministic_id("project-contract-revision", {"project_id": content.project_id, "content": content.model_dump(mode="json")}),
            contract_id=contract_id,
            project_id=content.project_id,
            revision_number=revision_number,
            previous_revision_id=previous.current_revision_id if previous else None,
            status=status,
            created_by=created_by,
            content=content,
            semantic_fingerprint=_contract_semantic_fingerprint(content),
            content_fingerprint=_content_fingerprint(content.model_dump(mode="json")),
            provenance=provenance,
            evidence_references=evidence_references or [],
            freshness_state=freshness_state,
            supersedes_revision_id=previous.current_revision_id if previous else None,
        )
        revision.normalized_payload = revision.model_dump(mode="json")
        self.database.insert_project_contract_revision(revision)
        self.database.upsert_project_contract(_contract_from_revision(revision))
        return revision

    def approve_contract_revision(self, revision_id: str, *, approved_by: str = "manual") -> ProjectContractRecord:
        revision = self.get_contract_revision(revision_id)
        if revision is None:
            raise KeyError(f"Unknown project contract revision: {revision_id}")
        if revision.status == "approved":
            return self._current_contract(revision.project_id) or self._contract_from_revision(revision)
        approved = revision.model_copy(update={"status": "approved", "created_by": approved_by})
        approved.normalized_payload = approved.model_dump(mode="json")
        self.database.insert_project_contract_revision(approved)
        contract = self._contract_from_revision(approved)
        self.database.upsert_project_contract(contract)
        return contract

    def get_project_contract(self, project_id: str) -> ProjectContractRecord | None:
        return self._current_contract(project_id)

    def get_contract_revision(self, revision_id: str) -> ProjectContractRevisionRecord | None:
        return self.database.get_project_contract_revision(revision_id)

    def list_contract_revisions(self, project_id: str) -> list[ProjectContractRevisionRecord]:
        self._require_project(project_id)
        return self.database.list_project_contract_revisions(project_id)

    def current_approved_contract(self, project_id: str) -> ProjectContractRecord | None:
        self._require_project(project_id)
        contract = self._current_contract(project_id)
        if contract is None:
            return None
        if contract.status == "approved":
            return contract
        if contract.approved_revision_id is not None:
            revision = self.get_contract_revision(contract.approved_revision_id)
            if revision is not None:
                return self._contract_from_revision(revision)
        return None

    def create_contract_for_project(
        self,
        project_id: str,
        *,
        project_type: str | None = None,
        purpose: str | None = None,
        owner: str | None = None,
        authority_level: ProjectContractAuthorityLevel | None = None,
        status: ProjectContractStatus = "draft",
        provenance: ProgrammeProvenanceRecord | None = None,
        evidence_references: list[ProjectHealthEvidenceReference] | None = None,
        freshness_state: EvidenceFreshnessState = "unknown",
        additional_content: dict[str, Any] | None = None,
    ) -> ProjectContractRevisionRecord:
        project = self._require_project(project_id)
        content = self._content_from_project(project).model_copy(
            update={
                **({"project_type": project_type} if project_type is not None else {}),
                **({"purpose": purpose} if purpose is not None else {}),
                **({"owner": owner} if owner is not None else {}),
                **({"authority_level": authority_level} if authority_level is not None else {}),
                **(additional_content or {}),
            }
        )
        return self.create_contract_revision(
            content,
            status=status,
            provenance=provenance,
            evidence_references=evidence_references,
            freshness_state=freshness_state,
        )

    def _current_contract(self, project_id: str) -> ProjectContractRecord | None:
        contract = self.database.get_project_contract(project_id)
        if contract is not None and contract.current_revision is None and contract.current_revision_id is not None:
            revision = self.database.get_project_contract_revision(contract.current_revision_id)
            if revision is not None:
                contract.current_revision = revision
        return contract

    def _contract_from_revision(self, revision: ProjectContractRevisionRecord) -> ProjectContractRecord:
        current = self._current_contract(revision.project_id)
        if current is not None and current.current_revision_id == revision.revision_id:
            return current
        return ProjectContractRecord(
            contract_id=revision.contract_id,
            project_id=revision.project_id,
            current_revision_id=revision.revision_id,
            current_revision_number=revision.revision_number,
            approved_revision_id=revision.revision_id if revision.status == "approved" else None,
            approved_revision_number=revision.revision_number if revision.status == "approved" else None,
            status=revision.status,
            created_at=revision.created_at,
            updated_at=utc_now().isoformat(),
            content_fingerprint=revision.content_fingerprint,
            provenance=revision.provenance,
            freshness_state=revision.freshness_state,
            current_revision=revision,
        )

    def _content_from_project(self, project: ProjectConfig) -> ProjectContractContent:
        return ProjectContractContent(
            project_id=project.project_id,
            name=project.name,
            repository=str(project.root),
            status="approved",
            authority_level=cast(ProjectContractAuthorityLevel, project.access),
            owner=str(project.metadata.get("owner")) if project.metadata.get("owner") is not None else None,
            version="0.9.0",
            release_channel="released",
            documentation_roots=_documentation_roots(project),
            evidence_freshness_policy={
                "evidence_freshness_hours": project.health_rules.get("evidence_freshness_hours"),
                "required_paths": list(project.health_rules.get("required_paths") or []),
            },
            security_boundary="read_only",
        )

    def _validate_content(self, content: ProjectContractContent) -> None:
        project = self._require_project(content.project_id)
        if content.authority_level not in ("read_only", "gaia_local_state", "manual_handoff_only", "unsupported"):
            raise ValueError("Invalid project contract authority level")
        if content.status not in ("draft", "approved", "superseded", "retired"):
            raise ValueError("Invalid project contract status")
        if not content.repository.strip():
            raise ValueError("Project contract repository must not be empty")
        if content.evidence_freshness_policy is not None and not isinstance(content.evidence_freshness_policy, dict):
            raise ValueError("Project contract freshness policy must be a mapping")
        for reference in content.architecture_references:
            if self.database.get_architecture_entity(reference) is None:
                raise ValueError(f"Unknown architecture reference: {reference}")
        if content.project_id != project.project_id:
            raise ValueError("Project contract project identity mismatch")

    def _require_project(self, project_id: str) -> ProjectConfig:
        try:
            return self.settings.projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def _provenance_for_project(self, project: ProjectConfig, *, source_document: str) -> ProgrammeProvenanceRecord:
        return ProgrammeProvenanceRecord(
            source_project_id=project.project_id,
            repository=str(project.root),
            source_document=source_document,
            canonical_gaia_source="config",
            details={"project_name": project.name, "access": project.access},
        )

    def _provenance_for_content(self, content: ProjectContractContent) -> ProgrammeProvenanceRecord:
        return ProgrammeProvenanceRecord(
            source_project_id=content.project_id,
            repository=content.repository,
            canonical_gaia_source="contract",
            details={"authority_level": content.authority_level, "version": content.version},
        )

    def _contract_id(self, project_id: str) -> str:
        return f"project-contract:{project_id}"


class ArchitectureRegistryService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        audit: AuditRecorder | None = None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.audit = audit

    def bootstrap_from_settings(self) -> list[ArchitectureEntityRecord]:
        bootstrapped: list[ArchitectureEntityRecord] = []
        for project in sorted(self.settings.projects.values(), key=lambda item: item.project_id):
            bootstrapped.append(self.ensure_project_entity(project))
        return bootstrapped

    def ensure_project_entity(self, project: ProjectConfig) -> ArchitectureEntityRecord:
        content = self._project_entity_content(project)
        revision = self.create_entity_revision(
            content,
            status="approved",
            created_by="bootstrap",
            evidence_references=[],
            freshness_state="fresh",
        )
        return self.get_entity(revision.entity_id) or self._entity_from_revision(revision)

    def register_entity(
        self,
        content: ArchitectureEntityContent,
        *,
        status: ArchitectureEntityStatus = "draft",
        created_by: str = "system",
        provenance: ProgrammeProvenanceRecord | None = None,
        evidence_references: list[ProjectHealthEvidenceReference] | None = None,
        freshness_state: EvidenceFreshnessState = "unknown",
    ) -> ArchitectureEntityRevisionRecord:
        self._validate_content(content)
        existing = self.database.get_architecture_entity_revision_by_semantic(content.identity_key, _entity_semantic_fingerprint(content))
        if existing is not None:
            if status == "approved" and existing.status != "approved":
                return self.approve_entity_revision(existing.revision_id, approved_by=created_by).current_revision or existing
            return existing
        entity_id = self._entity_id(content)
        revision_number = self.database.next_architecture_entity_revision_number(entity_id)
        previous = self.database.get_architecture_entity(entity_id)
        provenance = provenance or content.provenance
        if self.audit is not None:
            event = self.audit.record(
                category="programme_registry",
                operation="register_architecture_entity_revision",
                project_id=content.owning_project_or_domain,
                outcome="success",
                metadata={"entity_id": entity_id, "revision_number": revision_number, "status": status},
            )
            provenance = provenance.model_copy(update={"details": {**provenance.details, "audit_event_id": event.event_id}})
        revision = ArchitectureEntityRevisionRecord(
            revision_id=_deterministic_id("architecture-entity-revision", {"entity_id": entity_id, "content": content.model_dump(mode="json")}),
            entity_id=entity_id,
            identity_key=content.identity_key,
            revision_number=revision_number,
            previous_revision_id=previous.current_revision_id if previous else None,
            status=status,
            created_by=created_by,
            content=content,
            semantic_fingerprint=_entity_semantic_fingerprint(content),
            content_fingerprint=_content_fingerprint(content.model_dump(mode="json")),
            provenance=provenance,
            evidence_references=evidence_references or [],
            freshness_state=freshness_state,
            supersedes_revision_id=previous.current_revision_id if previous else None,
        )
        revision.normalized_payload = revision.model_dump(mode="json")
        if previous is None:
            self.database.upsert_architecture_entity(
                ArchitectureEntityRecord(
                    entity_id=entity_id,
                    identity_key=content.identity_key,
                    kind=content.kind,
                    name=content.name,
                    owning_project_or_domain=content.owning_project_or_domain,
                    repository=content.repository,
                    source_reference=content.source_reference,
                    current_revision_id=None,
                    current_revision_number=0,
                    status="draft",
                    freshness_state=freshness_state,
                    provenance=provenance,
                )
            )
        self.database.insert_architecture_entity_revision(revision)
        self.database.upsert_architecture_entity(self._entity_from_revision(revision))
        return revision

    def create_entity_revision(
        self,
        content: ArchitectureEntityContent,
        *,
        status: ArchitectureEntityStatus = "draft",
        created_by: str = "system",
        provenance: ProgrammeProvenanceRecord | None = None,
        evidence_references: list[ProjectHealthEvidenceReference] | None = None,
        freshness_state: EvidenceFreshnessState = "unknown",
    ) -> ArchitectureEntityRevisionRecord:
        return self.register_entity(
            content,
            status=status,
            created_by=created_by,
            provenance=provenance,
            evidence_references=evidence_references,
            freshness_state=freshness_state,
        )

    def get_entity(self, entity_id: str) -> ArchitectureEntityRecord | None:
        return self.database.get_architecture_entity(entity_id)

    def get_entity_revision(self, revision_id: str) -> ArchitectureEntityRevisionRecord | None:
        return self.database.get_architecture_entity_revision(revision_id)

    def list_entities(self) -> list[ArchitectureEntityRecord]:
        return self.database.list_architecture_entities()

    def list_entities_by_project(self, project_id: str) -> list[ArchitectureEntityRecord]:
        return self.database.list_architecture_entities(project_id=project_id)

    def list_entities_by_kind(self, kind: ArchitectureEntityKind) -> list[ArchitectureEntityRecord]:
        return self.database.list_architecture_entities(kind=kind)

    def list_entity_revisions(self, entity_id: str) -> list[ArchitectureEntityRevisionRecord]:
        return self.database.list_architecture_entity_revisions(entity_id)

    def register_relationship(
        self,
        content: ArchitectureRelationshipContent,
        *,
        status: ArchitectureRelationshipStatus = "draft",
        created_by: str = "system",
        provenance: ProgrammeProvenanceRecord | None = None,
        evidence_references: list[ProjectHealthEvidenceReference] | None = None,
        freshness_state: EvidenceFreshnessState = "unknown",
    ) -> ArchitectureRelationshipRevisionRecord:
        self._validate_relationship_content(content)
        existing = self.database.get_architecture_relationship_revision_by_semantic(content.identity_key, _relationship_semantic_fingerprint(content))
        if existing is not None:
            if status == "approved" and existing.status != "approved":
                return self.approve_relationship_revision(existing.revision_id, approved_by=created_by).current_revision or existing
            return existing
        relationship_id = self._relationship_id(content)
        revision_number = self.database.next_architecture_relationship_revision_number(relationship_id)
        previous = self.database.get_architecture_relationship(relationship_id)
        provenance = provenance or content.provenance
        if self.audit is not None:
            event = self.audit.record(
                category="programme_registry",
                operation="register_architecture_relationship_revision",
                project_id=content.provenance.source_project_id,
                outcome="success",
                metadata={"relationship_id": relationship_id, "revision_number": revision_number, "status": status},
            )
            provenance = provenance.model_copy(update={"details": {**provenance.details, "audit_event_id": event.event_id}})
        revision = ArchitectureRelationshipRevisionRecord(
            revision_id=_deterministic_id("architecture-relationship-revision", {"relationship_id": relationship_id, "content": content.model_dump(mode="json")}),
            relationship_id=relationship_id,
            identity_key=content.identity_key,
            revision_number=revision_number,
            previous_revision_id=previous.current_revision_id if previous else None,
            status=status,
            created_by=created_by,
            content=content,
            semantic_fingerprint=_relationship_semantic_fingerprint(content),
            content_fingerprint=_content_fingerprint(content.model_dump(mode="json")),
            provenance=provenance,
            evidence_references=evidence_references or content.evidence_references,
            freshness_state=freshness_state,
            supersedes_revision_id=previous.current_revision_id if previous else None,
        )
        revision.normalized_payload = revision.model_dump(mode="json")
        if previous is None:
            self.database.upsert_architecture_relationship(
                ArchitectureRelationshipRecord(
                    relationship_id=relationship_id,
                    identity_key=content.identity_key,
                    relationship_type=content.relationship_type,
                    source_entity_id=content.source_entity_id,
                    target_entity_id=content.target_entity_id,
                    current_revision_id=None,
                    current_revision_number=0,
                    status="draft",
                    freshness_state=freshness_state,
                    provenance=provenance,
                )
            )
        self.database.insert_architecture_relationship_revision(revision)
        self.database.upsert_architecture_relationship(self._relationship_from_revision(revision))
        return revision

    def approve_entity_revision(self, revision_id: str, *, approved_by: str = "manual") -> ArchitectureEntityRecord:
        revision = self.get_entity_revision(revision_id)
        if revision is None:
            raise KeyError(f"Unknown architecture entity revision: {revision_id}")
        if revision.status != "approved":
            revision = revision.model_copy(update={"status": "approved", "created_by": approved_by})
            revision.normalized_payload = revision.model_dump(mode="json")
            self.database.insert_architecture_entity_revision(revision)
        entity = self._entity_from_revision(revision)
        self.database.upsert_architecture_entity(entity)
        return entity

    def approve_relationship_revision(self, revision_id: str, *, approved_by: str = "manual") -> ArchitectureRelationshipRecord:
        revision = self.get_relationship_revision(revision_id)
        if revision is None:
            raise KeyError(f"Unknown architecture relationship revision: {revision_id}")
        if revision.status != "approved":
            revision = revision.model_copy(update={"status": "approved", "created_by": approved_by})
            revision.normalized_payload = revision.model_dump(mode="json")
            self.database.insert_architecture_relationship_revision(revision)
        relationship = self._relationship_from_revision(revision)
        self.database.upsert_architecture_relationship(relationship)
        return relationship

    def create_relationship_revision(
        self,
        content: ArchitectureRelationshipContent,
        *,
        status: ArchitectureRelationshipStatus = "draft",
        created_by: str = "system",
        provenance: ProgrammeProvenanceRecord | None = None,
        evidence_references: list[ProjectHealthEvidenceReference] | None = None,
        freshness_state: EvidenceFreshnessState = "unknown",
    ) -> ArchitectureRelationshipRevisionRecord:
        return self.register_relationship(
            content,
            status=status,
            created_by=created_by,
            provenance=provenance,
            evidence_references=evidence_references,
            freshness_state=freshness_state,
        )

    def get_relationship(self, relationship_id: str) -> ArchitectureRelationshipRecord | None:
        return self.database.get_architecture_relationship(relationship_id)

    def get_relationship_revision(self, revision_id: str) -> ArchitectureRelationshipRevisionRecord | None:
        return self.database.get_architecture_relationship_revision(revision_id)

    def list_relationships(self) -> list[ArchitectureRelationshipRecord]:
        return self.database.list_architecture_relationships()

    def list_relationships_by_source(self, source_entity_id: str) -> list[ArchitectureRelationshipRecord]:
        return self.database.list_architecture_relationships(source_entity_id=source_entity_id)

    def list_relationships_by_target(self, target_entity_id: str) -> list[ArchitectureRelationshipRecord]:
        return self.database.list_architecture_relationships(target_entity_id=target_entity_id)

    def list_relationships_by_type(self, relationship_type: ArchitectureRelationshipType) -> list[ArchitectureRelationshipRecord]:
        return self.database.list_architecture_relationships(relationship_type=relationship_type)

    def list_relationship_revisions(self, relationship_id: str) -> list[ArchitectureRelationshipRevisionRecord]:
        return self.database.list_architecture_relationship_revisions(relationship_id)

    def _project_entity_content(self, project: ProjectConfig) -> ArchitectureEntityContent:
        return ArchitectureEntityContent(
            identity_key=project.project_id,
            kind="project",
            name=project.name,
            owning_project_or_domain=project.project_id,
            repository=str(project.root),
            source_reference="config/projects.yaml",
            status="approved",
            freshness_state="fresh",
            provenance=ProgrammeProvenanceRecord(
                source_project_id=project.project_id,
                repository=str(project.root),
                source_document="config/projects.yaml",
                canonical_gaia_source="config",
                details={"project_name": project.name, "access": project.access, "owner": project.metadata.get("owner")},
            ),
        )

    def _entity_id(self, content: ArchitectureEntityContent) -> str:
        return f"architecture-entity:{content.kind}:{content.identity_key}"

    def _relationship_id(self, content: ArchitectureRelationshipContent) -> str:
        return f"architecture-relationship:{content.relationship_type}:{content.source_entity_id}:{content.target_entity_id}"

    def _entity_from_revision(self, revision: ArchitectureEntityRevisionRecord) -> ArchitectureEntityRecord:
        current = self.get_entity(revision.entity_id)
        if current is not None and current.current_revision_id == revision.revision_id:
            return current
        return ArchitectureEntityRecord(
            entity_id=revision.entity_id,
            identity_key=revision.content.identity_key,
            kind=revision.content.kind,
            name=revision.content.name,
            owning_project_or_domain=revision.content.owning_project_or_domain,
            repository=revision.content.repository,
            source_reference=revision.content.source_reference,
            current_revision_id=revision.revision_id,
            current_revision_number=revision.revision_number,
            status=revision.status,
            freshness_state=revision.freshness_state,
            provenance=revision.provenance,
            current_revision=revision,
            content_fingerprint=revision.content_fingerprint,
        )

    def _relationship_from_revision(self, revision: ArchitectureRelationshipRevisionRecord) -> ArchitectureRelationshipRecord:
        current = self.get_relationship(revision.relationship_id)
        if current is not None and current.current_revision_id == revision.revision_id:
            return current
        return ArchitectureRelationshipRecord(
            relationship_id=revision.relationship_id,
            identity_key=revision.content.identity_key,
            relationship_type=revision.content.relationship_type,
            source_entity_id=revision.content.source_entity_id,
            target_entity_id=revision.content.target_entity_id,
            current_revision_id=revision.revision_id,
            current_revision_number=revision.revision_number,
            status=revision.status,
            freshness_state=revision.freshness_state,
            provenance=revision.provenance,
            current_revision=revision,
            content_fingerprint=revision.content_fingerprint,
        )

    def _validate_content(self, content: ArchitectureEntityContent) -> None:
        if content.kind == "project" and content.identity_key not in self.settings.projects:
            raise KeyError(f"Unknown project: {content.identity_key}")
        if content.repository is not None and not content.repository.strip():
            raise ValueError("Architecture entity repository must not be empty")
        if content.status not in ("draft", "approved", "superseded", "retired"):
            raise ValueError("Invalid architecture entity status")
        if content.freshness_state not in ("fresh", "stale", "unknown", "unavailable"):
            raise ValueError("Invalid freshness state")

    def _validate_relationship_content(self, content: ArchitectureRelationshipContent) -> None:
        if content.status not in ("draft", "approved", "superseded", "retired"):
            raise ValueError("Invalid relationship status")
        if content.freshness_state not in ("fresh", "stale", "unknown", "unavailable"):
            raise ValueError("Invalid freshness state")
        if content.source_entity_id == content.target_entity_id:
            raise ValueError("Source and target entities must differ")
        if self.database.get_architecture_entity(content.source_entity_id) is None:
            raise KeyError(f"Unknown source entity: {content.source_entity_id}")
        if self.database.get_architecture_entity(content.target_entity_id) is None:
            raise KeyError(f"Unknown target entity: {content.target_entity_id}")


def _normalise_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _content_fingerprint(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _deterministic_id(prefix: str, payload: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"gaia:{prefix}:{_content_fingerprint(payload)}"))


def _contract_semantic_fingerprint(content: ProjectContractContent) -> str:
    payload = content.model_dump(mode="json", exclude={"status"})
    return _content_fingerprint(payload)


def _entity_semantic_fingerprint(content: ArchitectureEntityContent) -> str:
    payload = content.model_dump(mode="json", exclude={"status"})
    return _content_fingerprint(payload)


def _relationship_semantic_fingerprint(content: ArchitectureRelationshipContent) -> str:
    payload = content.model_dump(mode="json", exclude={"status"})
    return _content_fingerprint(payload)


def _contract_from_revision(revision: ProjectContractRevisionRecord) -> ProjectContractRecord:
    return ProjectContractRecord(
        contract_id=revision.contract_id,
        project_id=revision.project_id,
        current_revision_id=revision.revision_id,
        current_revision_number=revision.revision_number,
        approved_revision_id=revision.revision_id if revision.status == "approved" else None,
        approved_revision_number=revision.revision_number if revision.status == "approved" else None,
        status=revision.status,
        created_at=revision.created_at,
        updated_at=utc_now().isoformat(),
        content_fingerprint=revision.content_fingerprint,
        provenance=revision.provenance,
        freshness_state=revision.freshness_state,
        current_revision=revision,
    )


def _documentation_roots(project: ProjectConfig) -> list[str]:
    roots: list[str] = []
    for path in project.important_paths:
        if path.lower().startswith("docs"):
            roots.append(path)
    return _normalise_strings(roots)
