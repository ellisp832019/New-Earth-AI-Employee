from __future__ import annotations

import hashlib
import json
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gaia.config import Settings
from gaia.db import Database
from gaia.dependency_graph import (
    DependencyGraphDependencyRecord,
    DependencyGraphNode,
    DependencyGraphService,
    DependencyGraphSnapshot,
)
from gaia.models import ProjectConfig, WorkPackageRecord, utc_now
from gaia.programme_registry import (
    ArchitectureEntityKind,
    ArchitectureEntityRecord,
    ArchitectureRegistryService,
    ProgrammeProvenanceRecord,
    ProjectContractContent,
    ProjectContractRecord,
    ProjectContractService,
)

ChangeImpactChangeType = Literal[
    "API_CHANGE",
    "PACKAGE_UPGRADE",
    "SCHEMA_CHANGE",
    "FIRMWARE_PROTOCOL_CHANGE",
    "REPOSITORY_RESTRUCTURE",
    "RELEASE_VERSION_CHANGE",
    "HARDWARE_INTERFACE_CHANGE",
    "SHARED_LIBRARY_CHANGE",
    "PROJECT_CONTRACT_CHANGE",
]

ChangeProposalStatus = Literal["draft", "analysed", "superseded", "retired"]
ChangeProposalTargetKind = Literal[
    "architecture_entity",
    "project",
    "project_contract",
    "api_contract",
    "schema",
    "release_contract",
    "data_contract",
    "protocol_contract",
    "package",
    "library",
    "hardware",
    "work_package",
]

ChangeImpactScope = Literal["direct", "transitive"]
ChangeImpactRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"]
ChangeImpactFindingType = Literal[
    "UNKNOWN_TARGET",
    "UNRESOLVED_DEPENDENCY",
    "MISSING_CONTRACT",
    "STALE_GRAPH_INPUT",
    "UNAVAILABLE_PROJECT",
    "MISSING_VERSION_INFORMATION",
    "CONFLICTING_RELATIONSHIPS",
    "INSUFFICIENT_WORK_PACKAGE_LINKAGE",
    "INSUFFICIENT_TEST_METADATA",
    "UNVERIFIED_CONTRACT_IMPACT",
    "INSUFFICIENT_EVIDENCE",
]
ChangeImpactReasonCode = Literal[
    "TARGET_ENTITY",
    "TARGET_PROJECT",
    "TARGET_PROJECT_CONTRACT",
    "TARGET_WORK_PACKAGE",
    "CONTRACT_REFERENCE",
    "DIRECT_CONSUMER",
    "TRANSITIVE_DEPENDENT",
    "SHARED_DEPENDENCY",
    "CONTRACT_CONSUMER",
    "SCHEMA_CONSUMER",
    "RELEASE_COUPLING",
    "VERSION_CONSTRAINT",
    "BLOCKED_BY_UNRESOLVED_DEPENDENCY",
    "STALE_EVIDENCE",
    "UNKNOWN_TARGET",
    "MISSING_CONTRACT",
    "MISSING_VERSION_INFORMATION",
    "UNVERIFIED_CONTRACT_IMPACT",
    "INSUFFICIENT_EVIDENCE",
]


class ChangeProposalEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evidence_kind: str
    evidence_id: str | None = None
    description: str
    freshness: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeProposalTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_kind: ChangeProposalTargetKind
    target_id: str
    label: str | None = None
    project_id: str | None = None
    proposed_changes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target_id", "label", "project_id")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("target_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target_id must not be empty")
        return value.strip()


class ChangeProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    proposal_id: str = ""
    revision: int = Field(default=1, ge=1)
    title: str
    origin_project: str
    objective: str
    change_type: ChangeImpactChangeType
    target_entities: list[ChangeProposalTarget] = Field(default_factory=list)
    proposed_contract_changes: dict[str, Any] = Field(default_factory=dict)
    affected_versions: list[str] = Field(default_factory=list)
    evidence: list[ChangeProposalEvidenceReference] = Field(default_factory=list)
    impact_result: dict[str, Any] | None = None
    risk: str = "UNKNOWN"
    blocked_by: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    rollback_concept: str = ""
    recommended_order: list[str] = Field(default_factory=list)
    status: ChangeProposalStatus = "draft"
    human_decision: str | None = None

    @field_validator("proposal_id", "title", "origin_project", "objective", "rollback_concept", "human_decision")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("proposal_id")
    @classmethod
    def _allow_empty(cls, value: str) -> str:
        return value.strip()

    @field_validator("origin_project")
    @classmethod
    def _origin_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("origin_project must not be empty")
        return value

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        if value not in {"draft", "analysed", "superseded", "retired"}:
            raise ValueError("Invalid proposal status")
        return value


class ChangeImpactTargetResolution(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resolution_id: str
    target_kind: ChangeProposalTargetKind
    target_id: str
    resolution_state: Literal["resolved", "unknown", "conflicting", "unsupported"] = "resolved"
    resolved_project_id: str | None = None
    resolved_entity_id: str | None = None
    resolved_contract_id: str | None = None
    resolved_work_package_id: str | None = None
    resolved_node_id: str | None = None
    resolved_label: str | None = None
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactEntityRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    impact_id: str
    impact_scope: ChangeImpactScope
    node_id: str
    architecture_entity_id: str
    entity_kind: ArchitectureEntityKind
    owning_project_or_domain: str | None = None
    reason_codes: list[ChangeImpactReasonCode] = Field(default_factory=list)
    path_node_ids: list[str] = Field(default_factory=list)
    path_edge_ids: list[str] = Field(default_factory=list)
    supporting_target_ids: list[str] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactProjectRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_impact_id: str
    project_id: str
    impact_scope: ChangeImpactScope
    supporting_entity_ids: list[str] = Field(default_factory=list)
    supporting_edge_ids: list[str] = Field(default_factory=list)
    supporting_target_ids: list[str] = Field(default_factory=list)
    path_node_ids: list[str] = Field(default_factory=list)
    path_edge_ids: list[str] = Field(default_factory=list)
    reason_codes: list[ChangeImpactReasonCode] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactContractRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contract_impact_id: str
    contract_kind: str
    contract_id: str
    project_id: str
    current_version: str | None = None
    declared_release_contract: str | None = None
    version_constraint: str | None = None
    impact_scope: ChangeImpactScope
    reason_codes: list[ChangeImpactReasonCode] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactReleaseRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    release_impact_id: str
    project_id: str
    current_version: str | None = None
    declared_release_contract: str | None = None
    version_constraint: str | None = None
    impact_scope: ChangeImpactScope
    reason_codes: list[ChangeImpactReasonCode] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactWorkPackageRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    work_package_impact_id: str
    work_package_id: str
    project_id: str
    revision_id: str | None = None
    revision_number: int | None = None
    impact_scope: ChangeImpactScope
    reason_codes: list[ChangeImpactReasonCode] = Field(default_factory=list)
    supporting_entity_ids: list[str] = Field(default_factory=list)
    supporting_edge_ids: list[str] = Field(default_factory=list)
    supporting_target_ids: list[str] = Field(default_factory=list)
    evidence_fingerprints: list[str] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactValidationReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    validation_id: str
    project_id: str
    reference_kind: Literal["test_command", "build_command", "documentation_root", "release_process_reference"]
    reference: str
    description: str
    source_contract_id: str | None = None
    source_contract_revision_id: str | None = None
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactRefreshRequirement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    refresh_requirement_id: str
    subject_kind: Literal["proposal", "project", "entity", "contract", "graph", "work_package"]
    subject_id: str
    refresh_kind: str
    reason_code: ChangeImpactReasonCode
    description: str
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactSequencingConstraint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sequencing_constraint_id: str
    prerequisite_project_id: str | None = None
    prerequisite_entity_id: str | None = None
    dependent_project_id: str | None = None
    dependent_entity_id: str | None = None
    reason_code: ChangeImpactReasonCode
    description: str
    supporting_node_ids: list[str] = Field(default_factory=list)
    supporting_edge_ids: list[str] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")

    finding_id: str
    finding_type: ChangeImpactFindingType
    severity: Literal["info", "warning", "critical"] = "warning"
    summary: str
    explanation: str
    affected_project_id: str | None = None
    affected_entity_id: str | None = None
    related_target_ids: list[str] = Field(default_factory=list)
    related_node_ids: list[str] = Field(default_factory=list)
    related_edge_ids: list[str] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactRiskFactor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    factor_id: str
    description: str
    value: int
    weight: int
    contribution: int
    evidence_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactRiskResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk_level: ChangeImpactRiskLevel = "UNKNOWN"
    score: int = 0
    factor_codes: list[str] = Field(default_factory=list)
    factors: list[ChangeImpactRiskFactor] = Field(default_factory=list)
    evidence_fingerprints: list[str] = Field(default_factory=list)
    explanation: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ChangeImpactResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    analysis_timestamp: str = Field(default_factory=lambda: utc_now().isoformat())
    proposal_id: str
    proposal_revision: int
    proposal_identity_fingerprint: str
    proposal_revision_fingerprint: str
    graph_fingerprint: str
    proposal: ChangeProposal
    target_resolutions: list[ChangeImpactTargetResolution] = Field(default_factory=list)
    direct_entities: list[ChangeImpactEntityRecord] = Field(default_factory=list)
    transitive_entities: list[ChangeImpactEntityRecord] = Field(default_factory=list)
    affected_projects: list[ChangeImpactProjectRecord] = Field(default_factory=list)
    affected_contracts: list[ChangeImpactContractRecord] = Field(default_factory=list)
    affected_releases: list[ChangeImpactReleaseRecord] = Field(default_factory=list)
    affected_work_packages: list[ChangeImpactWorkPackageRecord] = Field(default_factory=list)
    validation_references: list[ChangeImpactValidationReference] = Field(default_factory=list)
    refresh_requirements: list[ChangeImpactRefreshRequirement] = Field(default_factory=list)
    sequencing_constraints: list[ChangeImpactSequencingConstraint] = Field(default_factory=list)
    unknown_findings: list[ChangeImpactFinding] = Field(default_factory=list)
    risk: ChangeImpactRiskResult = Field(default_factory=ChangeImpactRiskResult)
    freshness_state: str = "unknown"
    trust_state: str = "unknown"
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    impact_fingerprint: str = ""


class ChangeImpactService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        project_contract_service: ProjectContractService,
        architecture_registry_service: ArchitectureRegistryService,
        dependency_graph_service: DependencyGraphService,
    ) -> None:
        self.settings = settings
        self.database = database
        self.project_contract_service = project_contract_service
        self.architecture_registry_service = architecture_registry_service
        self.dependency_graph_service = dependency_graph_service

    def analyse_proposal(self, proposal: ChangeProposal | dict[str, Any]) -> ChangeImpactResult:
        normalized = self._normalize_proposal(proposal)
        graph = self.dependency_graph_service.build_graph()
        entity_index = {entity.entity_id: entity for entity in self.architecture_registry_service.list_entities()}
        entity_index_by_identity = {entity.identity_key: entity for entity in entity_index.values()}
        project_nodes: dict[str, DependencyGraphNode] = {
            node.owning_project_or_domain: node
            for node in graph.nodes
            if node.entity_kind == "project" and node.owning_project_or_domain is not None
        }

        proposal_identity_fingerprint = self._proposal_identity_fingerprint(normalized)
        proposal_revision_fingerprint = self._proposal_revision_fingerprint(normalized)

        target_resolutions = self._resolve_targets(
            normalized,
            graph=graph,
            entity_index=entity_index,
            entity_index_by_identity=entity_index_by_identity,
        )
        if not normalized.target_entities and not normalized.proposed_contract_changes:
            target_resolutions.append(
                ChangeImpactTargetResolution(
                    resolution_id=_deterministic_id(
                        "change-impact-target-resolution",
                        {"proposal_revision_fingerprint": proposal_revision_fingerprint, "target_id": "insufficient_evidence"},
                    ),
                    target_kind="project",
                    target_id=normalized.origin_project,
                    resolution_state="unknown",
                    freshness_state="unknown",
                    trust_state="unknown",
                    details={"reason": "no_targets_or_contract_changes"},
                )
            )

        direct_entities, transitive_entities, affected_projects, affected_contracts, affected_releases = self._collect_entity_project_contract_release_impacts(
            normalized,
            graph=graph,
            project_nodes=project_nodes,
            target_resolutions=target_resolutions,
        )
        affected_work_packages = self._collect_work_package_impacts(affected_projects, target_resolutions)
        validation_references = self._collect_validation_references(affected_contracts, target_resolutions)
        refresh_requirements = self._collect_refresh_requirements(
            normalized,
            target_resolutions,
            direct_entities,
            transitive_entities,
            affected_contracts,
            affected_releases,
            affected_work_packages,
        )
        sequencing_constraints = self._collect_sequencing_constraints(direct_entities, target_resolutions)
        unknown_findings = self._collect_unknown_findings(
            normalized,
            target_resolutions,
            affected_contracts,
            validation_references,
            affected_work_packages,
            graph,
        )
        risk = self._calculate_risk(
            normalized,
            direct_entities,
            transitive_entities,
            affected_projects,
            affected_contracts,
            affected_releases,
            affected_work_packages,
            validation_references,
            refresh_requirements,
            sequencing_constraints,
            unknown_findings,
            graph,
        )

        freshness_state = self._combine_freshness(
            [
                *(item.freshness_state for item in target_resolutions),
                *(item.freshness_state for item in direct_entities),
                *(item.freshness_state for item in transitive_entities),
                *(item.freshness_state for item in affected_projects),
                *(item.freshness_state for item in affected_contracts),
                *(item.freshness_state for item in affected_releases),
                *(item.freshness_state for item in affected_work_packages),
                *(item.freshness_state for item in validation_references),
                *(item.freshness_state for item in refresh_requirements),
                *(item.freshness_state for item in sequencing_constraints),
                *(item.freshness_state for item in unknown_findings),
            ]
        )
        trust_state = self._combine_trust(
            [
                *(item.trust_state for item in target_resolutions),
                *(item.trust_state for item in direct_entities),
                *(item.trust_state for item in transitive_entities),
                *(item.trust_state for item in affected_projects),
                *(item.trust_state for item in affected_contracts),
                *(item.trust_state for item in affected_releases),
                *(item.trust_state for item in affected_work_packages),
                *(item.trust_state for item in validation_references),
                *(item.trust_state for item in refresh_requirements),
                *(item.trust_state for item in sequencing_constraints),
                *(item.trust_state for item in unknown_findings),
            ]
        )

        result = ChangeImpactResult(
            analysis_id=_deterministic_id(
                "change-impact-analysis",
                {
                    "proposal_revision_fingerprint": proposal_revision_fingerprint,
                    "graph_fingerprint": graph.graph_fingerprint,
                },
            ),
            proposal_id=normalized.proposal_id,
            proposal_revision=normalized.revision,
            proposal_identity_fingerprint=proposal_identity_fingerprint,
            proposal_revision_fingerprint=proposal_revision_fingerprint,
            graph_fingerprint=graph.graph_fingerprint,
            proposal=normalized,
            target_resolutions=sorted(target_resolutions, key=lambda item: (item.target_kind, item.target_id, item.resolution_id)),
            direct_entities=sorted(direct_entities, key=lambda item: (item.node_id, item.impact_id)),
            transitive_entities=sorted(transitive_entities, key=lambda item: (item.node_id, item.impact_id)),
            affected_projects=sorted(affected_projects, key=lambda item: (item.project_id, item.project_impact_id)),
            affected_contracts=sorted(affected_contracts, key=lambda item: (item.project_id, item.contract_impact_id)),
            affected_releases=sorted(affected_releases, key=lambda item: (item.project_id, item.release_impact_id)),
            affected_work_packages=sorted(affected_work_packages, key=lambda item: (item.project_id, item.work_package_id, item.work_package_impact_id)),
            validation_references=sorted(validation_references, key=lambda item: (item.project_id, item.reference_kind, item.reference, item.validation_id)),
            refresh_requirements=sorted(refresh_requirements, key=lambda item: (item.subject_kind, item.subject_id, item.refresh_kind, item.refresh_requirement_id)),
            sequencing_constraints=sorted(
                sequencing_constraints,
                key=lambda item: (
                    item.prerequisite_project_id or "",
                    item.prerequisite_entity_id or "",
                    item.dependent_project_id or "",
                    item.dependent_entity_id or "",
                    item.sequencing_constraint_id,
                ),
            ),
            unknown_findings=sorted(unknown_findings, key=lambda item: (item.finding_type, item.severity, item.finding_id)),
            risk=risk,
            freshness_state=freshness_state,
            trust_state=trust_state,
            provenance_references=_dedupe_provenance(
                [*(item for item in self._proposal_provenance(normalized)), *(item for item in self._graph_provenance(graph))]
            ),
        )
        result.impact_fingerprint = _content_fingerprint(self._impact_payload(result))
        return result

    def analyze_proposal(self, proposal: ChangeProposal | dict[str, Any]) -> ChangeImpactResult:
        return self.analyse_proposal(proposal)

    def analyze_change_impact(self, proposal: ChangeProposal | dict[str, Any]) -> ChangeImpactResult:
        return self.analyse_proposal(proposal)

    def analyse_change_impact(self, proposal: ChangeProposal | dict[str, Any]) -> ChangeImpactResult:
        return self.analyse_proposal(proposal)

    def change_impact(self, proposal: ChangeProposal | dict[str, Any]) -> ChangeImpactResult:
        return self.analyse_proposal(proposal)

    def _normalize_proposal(self, proposal: ChangeProposal | dict[str, Any]) -> ChangeProposal:
        normalized = ChangeProposal.model_validate(proposal)
        if not normalized.proposal_id:
            normalized = normalized.model_copy(update={"proposal_id": self._proposal_id(normalized)})
        normalized.target_entities = sorted(
            [ChangeProposalTarget.model_validate(item) for item in normalized.target_entities],
            key=lambda item: (item.target_kind, item.target_id, item.label or "", item.project_id or ""),
        )
        normalized.affected_versions = _dedupe_preserve_order(normalized.affected_versions)
        normalized.blocked_by = _dedupe_preserve_order(normalized.blocked_by)
        normalized.depends_on = _dedupe_preserve_order(normalized.depends_on)
        normalized.required_validation = _dedupe_preserve_order(normalized.required_validation)
        normalized.recommended_order = _dedupe_preserve_order(normalized.recommended_order)
        normalized.evidence = sorted(normalized.evidence, key=lambda item: (item.evidence_kind, item.evidence_id or "", item.description))
        normalized.proposed_contract_changes = self._normalise_value(normalized.proposed_contract_changes)
        normalized.impact_result = self._normalise_value(normalized.impact_result) if normalized.impact_result is not None else None
        return normalized

    def _resolve_targets(
        self,
        proposal: ChangeProposal,
        *,
        graph: DependencyGraphSnapshot,
        entity_index: dict[str, ArchitectureEntityRecord],
        entity_index_by_identity: dict[str, ArchitectureEntityRecord],
    ) -> list[ChangeImpactTargetResolution]:
        resolutions: list[ChangeImpactTargetResolution] = []
        project_entities: dict[str, DependencyGraphNode] = {
            node.owning_project_or_domain: node
            for node in graph.nodes
            if node.entity_kind == "project" and node.owning_project_or_domain is not None
        }
        for target in proposal.target_entities:
            resolution = self._resolve_single_target(target, entity_index=entity_index, entity_index_by_identity=entity_index_by_identity, project_entities=project_entities)
            resolutions.append(resolution)
            if resolution.resolution_state != "resolved":
                continue
            preview_resolution = self._contract_preview_resolution(proposal, target, resolution)
            if preview_resolution is not None:
                resolutions.extend(preview_resolution)
        return _dedupe_target_resolutions(resolutions)

    def _resolve_single_target(
        self,
        target: ChangeProposalTarget,
        *,
        entity_index: dict[str, ArchitectureEntityRecord],
        entity_index_by_identity: dict[str, ArchitectureEntityRecord],
        project_entities: dict[str, DependencyGraphNode],
    ) -> ChangeImpactTargetResolution:
        details: dict[str, Any] = {}
        resolution_state: Literal["resolved", "unknown", "conflicting", "unsupported"] = "unknown"
        resolved_project_id: str | None = None
        resolved_entity_id: str | None = None
        resolved_contract_id: str | None = None
        resolved_work_package_id: str | None = None
        resolved_node_id: str | None = None
        resolved_label: str | None = target.label
        provenance_references: list[ProgrammeProvenanceRecord] = []
        freshness_state = "unknown"
        trust_state = "unknown"

        if target.target_kind == "project":
            try:
                project = self._project(target.target_id)
            except KeyError:
                details["reason"] = "unknown_project"
            else:
                resolved_project_id = project.project_id
                resolved_node_id = f"architecture-entity:project:{project.project_id}"
                resolved_entity_id = resolved_node_id
                resolved_label = resolved_label or project.name
                resolution_state = "resolved"
                contract = self.project_contract_service.current_approved_contract(project.project_id)
                if contract is not None:
                    resolved_contract_id = contract.contract_id
                    freshness_state = contract.freshness_state
                    trust_state = self._trust_from_freshness(contract.freshness_state)
                    provenance_references.append(contract.provenance)
                project_node = project_entities.get(project.project_id)
                if project_node is not None:
                    provenance_references.append(project_node.provenance)
                    freshness_state = self._merge_freshness(freshness_state, project_node.freshness_state)
                    trust_state = self._combine_trust([trust_state, self._trust_from_freshness(project_node.freshness_state)])
        elif target.target_kind == "project_contract":
            contract = self._resolve_contract_target(target.target_id)
            if contract is None:
                details["reason"] = "unknown_project_contract"
            else:
                resolved_project_id = contract.project_id
                resolved_contract_id = contract.contract_id
                resolved_label = resolved_label or contract.project_id
                resolution_state = "resolved"
                freshness_state = contract.freshness_state
                trust_state = self._trust_from_freshness(contract.freshness_state)
                provenance_references.append(contract.provenance)
                project_node = project_entities.get(contract.project_id)
                if project_node is not None:
                    resolved_node_id = project_node.node_id
                    resolved_entity_id = project_node.node_id
                    provenance_references.append(project_node.provenance)
                    freshness_state = self._merge_freshness(freshness_state, project_node.freshness_state)
                    trust_state = self._combine_trust([trust_state, self._trust_from_freshness(project_node.freshness_state)])
        elif target.target_kind == "work_package":
            package = self.database.get_work_package(target.target_id)
            if package is None:
                details["reason"] = "unknown_work_package"
            else:
                resolved_work_package_id = package.work_package_id
                resolved_project_id = package.project_id
                resolved_label = resolved_label or package.title or package.work_package_id
                resolution_state = "resolved"
                freshness_state = package.staleness_state
                trust_state = self._trust_from_freshness(package.staleness_state)
        else:
            entity = self._resolve_entity_target(target.target_id, entity_index, entity_index_by_identity, target.target_kind)
            if entity is None:
                details["reason"] = "unknown_entity"
            else:
                resolved_entity_id = entity.entity_id
                resolved_project_id = entity.owning_project_or_domain
                resolved_node_id = entity.entity_id
                resolved_label = resolved_label or entity.name
                resolution_state = "resolved"
                freshness_state = entity.freshness_state
                trust_state = self._trust_from_freshness(entity.freshness_state)
                provenance_references.append(entity.provenance)

        return ChangeImpactTargetResolution(
            resolution_id=_deterministic_id(
                "change-impact-target-resolution",
                {
                    "target_kind": target.target_kind,
                    "target_id": target.target_id,
                    "resolved_project_id": resolved_project_id,
                    "resolved_entity_id": resolved_entity_id,
                    "resolved_contract_id": resolved_contract_id,
                    "resolved_work_package_id": resolved_work_package_id,
                },
            ),
            target_kind=target.target_kind,
            target_id=target.target_id,
            resolution_state=resolution_state,
            resolved_project_id=resolved_project_id,
            resolved_entity_id=resolved_entity_id,
            resolved_contract_id=resolved_contract_id,
            resolved_work_package_id=resolved_work_package_id,
            resolved_node_id=resolved_node_id,
            resolved_label=resolved_label,
            provenance_references=_dedupe_provenance(provenance_references),
            freshness_state=freshness_state,
            trust_state=trust_state,
            details={**details, **({"project_id": target.project_id} if target.project_id else {}), **({k: self._normalise_value(v) for k, v in target.proposed_changes.items()} if target.proposed_changes else {})},
        )

    def _contract_preview_resolution(
        self,
        proposal: ChangeProposal,
        target: ChangeProposalTarget,
        resolution: ChangeImpactTargetResolution,
    ) -> list[ChangeImpactTargetResolution] | None:
        if target.target_kind not in {"project", "project_contract"}:
            return None
        contract = self._resolve_contract_target(target.target_id)
        if contract is None or contract.current_revision is None:
            return None
        projected = contract.current_revision.content.model_copy(
            update={
                **self._normalise_value(proposal.proposed_contract_changes),
                **self._normalise_value(target.proposed_changes),
            }
        )
        current_declarations = {
            (declaration["field"], declaration["reference"])
            for declaration in self._contract_declarations(contract.current_revision.content)
        }
        projected_declarations = {
            (declaration["field"], declaration["reference"])
            for declaration in self._contract_declarations(projected)
        }
        extra_declarations = sorted(projected_declarations - current_declarations)
        if not extra_declarations:
            return None
        resolutions: list[ChangeImpactTargetResolution] = []
        for field, reference in extra_declarations:
            entity = self._resolve_reference(reference)
            if entity is None:
                resolutions.append(
                    ChangeImpactTargetResolution(
                        resolution_id=_deterministic_id(
                            "change-impact-target-resolution",
                            {
                                "target_kind": target.target_kind,
                                "target_id": target.target_id,
                                "reference": reference,
                                "field": field,
                            },
                        ),
                        target_kind=target.target_kind,
                        target_id=f"{target.target_id}:{field}:{reference}",
                        resolution_state="unknown",
                        resolved_project_id=contract.project_id,
                        resolved_contract_id=contract.contract_id,
                        resolved_label=reference,
                        provenance_references=[contract.provenance],
                        freshness_state=contract.freshness_state,
                        trust_state=self._trust_from_freshness(contract.freshness_state),
                        details={"field": field, "declared_reference": reference, "reason": "projected_contract_reference_unresolved"},
                    )
                )
                continue
            resolutions.append(
                ChangeImpactTargetResolution(
                    resolution_id=_deterministic_id(
                        "change-impact-target-resolution",
                        {
                            "target_kind": target.target_kind,
                            "target_id": target.target_id,
                            "reference": reference,
                            "field": field,
                            "resolved_entity_id": entity.entity_id,
                        },
                    ),
                    target_kind=target.target_kind,
                    target_id=f"{target.target_id}:{field}:{reference}",
                    resolution_state="resolved",
                    resolved_project_id=entity.owning_project_or_domain,
                    resolved_entity_id=entity.entity_id,
                    resolved_node_id=entity.entity_id,
                    resolved_label=entity.name,
                    provenance_references=[contract.provenance, entity.provenance],
                    freshness_state=self._merge_freshness(contract.freshness_state, entity.freshness_state),
                    trust_state=self._combine_trust([self._trust_from_freshness(contract.freshness_state), self._trust_from_freshness(entity.freshness_state)]),
                    details={"field": field, "declared_reference": reference, "reason": "projected_contract_reference"},
                )
            )
        return resolutions

    def _collect_entity_project_contract_release_impacts(
        self,
        proposal: ChangeProposal,
        *,
        graph: DependencyGraphSnapshot,
        project_nodes: dict[str, DependencyGraphNode],
        target_resolutions: list[ChangeImpactTargetResolution],
    ) -> tuple[
        list[ChangeImpactEntityRecord],
        list[ChangeImpactEntityRecord],
        list[ChangeImpactProjectRecord],
        list[ChangeImpactContractRecord],
        list[ChangeImpactReleaseRecord],
    ]:
        direct_entities: dict[str, ChangeImpactEntityRecord] = {}
        transitive_entities: dict[str, ChangeImpactEntityRecord] = {}
        project_impacts: dict[str, ChangeImpactProjectRecord] = {}
        contract_impacts: dict[str, ChangeImpactContractRecord] = {}
        release_impacts: dict[str, ChangeImpactReleaseRecord] = {}

        for resolution in target_resolutions:
            root_node_id = resolution.resolved_node_id
            if root_node_id is None:
                continue
            root_node = self._node_by_id(graph.nodes, root_node_id)
            if root_node is None:
                continue
            direct_root = self._impact_entity_from_node(
                root_node,
                impact_scope="direct",
                reason_codes=["TARGET_ENTITY" if resolution.target_kind != "project_contract" else "TARGET_PROJECT_CONTRACT"],
                path_node_ids=[root_node.node_id],
                path_edge_ids=[],
                supporting_target_ids=[resolution.target_id],
                provenance_references=resolution.provenance_references or [root_node.provenance],
                freshness_state=resolution.freshness_state,
                trust_state=resolution.trust_state,
                details={"target_kind": resolution.target_kind, **resolution.details},
            )
            self._merge_entity_impact(direct_entities, direct_root)

            dependents = self.dependency_graph_service.dependents_of_entity(root_node.node_id, transitive=True)
            direct_dependents = [record for record in dependents if record.depth == 1]
            transitive_dependents = [record for record in dependents if record.depth > 1]
            for record in direct_dependents:
                impacted = self._impact_entity_from_dependency(
                    record,
                    impact_scope="direct",
                    reason_code=self._reason_code_for_dependency(resolution.target_kind, record),
                    supporting_target_ids=[resolution.target_id],
                )
                self._merge_entity_impact(direct_entities, impacted)
            for record in transitive_dependents:
                impacted = self._impact_entity_from_dependency(
                    record,
                    impact_scope="transitive",
                    reason_code="TRANSITIVE_DEPENDENT",
                    supporting_target_ids=[resolution.target_id],
                )
                self._merge_entity_impact(transitive_entities, impacted)

            if resolution.resolved_project_id is not None:
                project_node = project_nodes.get(resolution.resolved_project_id)
                if project_node is not None:
                    project_impact = ChangeImpactProjectRecord(
                        project_impact_id=_deterministic_id(
                            "change-impact-project",
                            {
                                "project_id": resolution.resolved_project_id,
                                "target_id": resolution.target_id,
                                "impact_scope": "direct",
                            },
                        ),
                        project_id=resolution.resolved_project_id,
                        impact_scope="direct",
                        supporting_entity_ids=[root_node.node_id],
                        supporting_edge_ids=[],
                        supporting_target_ids=[resolution.target_id],
                        path_node_ids=[project_node.node_id],
                        path_edge_ids=[],
                        reason_codes=["TARGET_PROJECT" if resolution.target_kind == "project" else "TARGET_PROJECT_CONTRACT"],
                        provenance_references=_dedupe_provenance([project_node.provenance, *resolution.provenance_references]),
                        freshness_state=self._merge_freshness(project_node.freshness_state, resolution.freshness_state),
                        trust_state=self._combine_trust([project_node.trust_state, resolution.trust_state]),
                        details={"target_kind": resolution.target_kind},
                    )
                    self._merge_project_impact(project_impacts, project_impact)
                contract = self._current_contract_for_project(resolution.resolved_project_id)
                if contract is not None:
                    current_revision = contract.current_revision
                    contract_impact = ChangeImpactContractRecord(
                        contract_impact_id=_deterministic_id(
                            "change-impact-contract",
                            {
                                "contract_id": contract.contract_id,
                                "target_id": resolution.target_id,
                                "change_type": proposal.change_type,
                            },
                        ),
                        contract_kind="project_contract",
                        contract_id=contract.contract_id,
                        project_id=contract.project_id,
                        current_version=current_revision.content.version if current_revision is not None else None,
                        declared_release_contract=current_revision.content.release_process_reference if current_revision is not None else None,
                        version_constraint=",".join(sorted(_dedupe_preserve_order(proposal.affected_versions))) or None,
                        impact_scope="direct",
                        reason_codes=["TARGET_PROJECT_CONTRACT" if resolution.target_kind == "project_contract" else "CONTRACT_REFERENCE"],
                        provenance_references=[contract.provenance],
                        freshness_state=contract.freshness_state,
                        trust_state=self._trust_from_freshness(contract.freshness_state),
                        details={"target_kind": resolution.target_kind},
                    )
                    self._merge_contract_impact(contract_impacts, contract_impact)
                    if current_revision is not None:
                        release_impact = ChangeImpactReleaseRecord(
                            release_impact_id=_deterministic_id(
                                "change-impact-release",
                                {
                                    "project_id": contract.project_id,
                                    "current_version": current_revision.content.version,
                                    "target_id": resolution.target_id,
                                },
                            ),
                            project_id=contract.project_id,
                            current_version=current_revision.content.version,
                            declared_release_contract=current_revision.content.release_process_reference,
                            version_constraint=current_revision.content.version,
                            impact_scope="direct",
                            reason_codes=["RELEASE_COUPLING" if current_revision.content.release_process_reference else "MISSING_VERSION_INFORMATION"],
                            provenance_references=[contract.provenance],
                            freshness_state=contract.freshness_state,
                            trust_state=self._trust_from_freshness(contract.freshness_state),
                            details={"target_kind": resolution.target_kind},
                        )
                        self._merge_release_impact(release_impacts, release_impact)

        for entity in [*direct_entities.values(), *transitive_entities.values()]:
            if entity.owning_project_or_domain is None:
                continue
            project_node = project_nodes.get(entity.owning_project_or_domain)
            if project_node is None:
                continue
            project_impact = ChangeImpactProjectRecord(
                project_impact_id=_deterministic_id(
                    "change-impact-project",
                    {
                        "project_id": entity.owning_project_or_domain,
                        "entity_id": entity.node_id,
                        "impact_scope": entity.impact_scope,
                    },
                ),
                project_id=entity.owning_project_or_domain,
                impact_scope=entity.impact_scope,
                supporting_entity_ids=[entity.node_id],
                supporting_edge_ids=list(entity.path_edge_ids),
                supporting_target_ids=list(entity.supporting_target_ids),
                path_node_ids=list(entity.path_node_ids),
                path_edge_ids=list(entity.path_edge_ids),
                reason_codes=list(entity.reason_codes),
                provenance_references=list(entity.provenance_references),
                freshness_state=entity.freshness_state,
                trust_state=entity.trust_state,
                details={"source_entity_id": entity.node_id},
            )
            self._merge_project_impact(project_impacts, project_impact)

        return (
            sorted(direct_entities.values(), key=lambda item: (item.node_id, item.impact_id)),
            sorted(transitive_entities.values(), key=lambda item: (item.node_id, item.impact_id)),
            sorted(project_impacts.values(), key=lambda item: (item.project_id, item.project_impact_id)),
            sorted(contract_impacts.values(), key=lambda item: (item.project_id, item.contract_impact_id)),
            sorted(release_impacts.values(), key=lambda item: (item.project_id, item.release_impact_id)),
        )

    def _collect_work_package_impacts(
        self,
        affected_projects: list[ChangeImpactProjectRecord],
        target_resolutions: list[ChangeImpactTargetResolution],
    ) -> list[ChangeImpactWorkPackageRecord]:
        affected_project_ids = {item.project_id for item in affected_projects}
        target_ids = {item.target_id for item in target_resolutions}
        impacted: dict[str, ChangeImpactWorkPackageRecord] = {}
        for package in self.database.list_work_packages():
            if package.project_id not in affected_project_ids:
                if not self._work_package_overlaps_targets(package, target_ids):
                    continue
            record = ChangeImpactWorkPackageRecord(
                work_package_impact_id=_deterministic_id(
                    "change-impact-work-package",
                    {
                        "work_package_id": package.work_package_id,
                        "project_id": package.project_id,
                    },
                ),
                work_package_id=package.work_package_id,
                project_id=package.project_id,
                revision_id=package.current_revision_id,
                revision_number=package.current_revision_number,
                impact_scope="direct" if package.project_id in affected_project_ids else "transitive",
                reason_codes=["TARGET_PROJECT" if package.project_id in affected_project_ids else "TRANSITIVE_DEPENDENT"],
                supporting_entity_ids=[],
                supporting_edge_ids=[],
                supporting_target_ids=sorted(target_ids & set(package.source_finding_ids + package.source_comparison_ids + package.source_snapshot_ids)),
                evidence_fingerprints=list(package.evidence_fingerprints),
                provenance_references=[],
                freshness_state=package.staleness_state,
                trust_state=self._trust_from_freshness(package.staleness_state),
                details={"approval_state": package.approval_state, "gate_state": package.gate_state},
            )
            impacted[record.work_package_id] = record
        return sorted(impacted.values(), key=lambda item: (item.project_id, item.work_package_id, item.work_package_impact_id))

    def _collect_validation_references(
        self,
        affected_contracts: list[ChangeImpactContractRecord],
        target_resolutions: list[ChangeImpactTargetResolution],
    ) -> list[ChangeImpactValidationReference]:
        validations: dict[str, ChangeImpactValidationReference] = {}
        for contract_impact in affected_contracts:
            contract = self._current_contract_for_project(contract_impact.project_id)
            if contract is None or contract.current_revision is None:
                continue
            content = contract.current_revision.content
            for command in content.test_commands:
                key = f"{contract.project_id}:test:{command}"
                validations[key] = ChangeImpactValidationReference(
                    validation_id=_deterministic_id("change-impact-validation", {"project_id": contract.project_id, "kind": "test_command", "command": command}),
                    project_id=contract.project_id,
                    reference_kind="test_command",
                    reference=command,
                    description=f"Project contract test command for {contract.project_id}.",
                    source_contract_id=contract.contract_id,
                    source_contract_revision_id=contract.current_revision_id,
                    freshness_state=contract.freshness_state,
                    trust_state=self._trust_from_freshness(contract.freshness_state),
                )
            for command in content.build_commands:
                key = f"{contract.project_id}:build:{command}"
                validations[key] = ChangeImpactValidationReference(
                    validation_id=_deterministic_id("change-impact-validation", {"project_id": contract.project_id, "kind": "build_command", "command": command}),
                    project_id=contract.project_id,
                    reference_kind="build_command",
                    reference=command,
                    description=f"Project contract build command for {contract.project_id}.",
                    source_contract_id=contract.contract_id,
                    source_contract_revision_id=contract.current_revision_id,
                    freshness_state=contract.freshness_state,
                    trust_state=self._trust_from_freshness(contract.freshness_state),
                )
            for root in content.documentation_roots:
                key = f"{contract.project_id}:doc:{root}"
                validations[key] = ChangeImpactValidationReference(
                    validation_id=_deterministic_id("change-impact-validation", {"project_id": contract.project_id, "kind": "documentation_root", "reference": root}),
                    project_id=contract.project_id,
                    reference_kind="documentation_root",
                    reference=root,
                    description=f"Documentation root referenced by the current approved contract for {contract.project_id}.",
                    source_contract_id=contract.contract_id,
                    source_contract_revision_id=contract.current_revision_id,
                    freshness_state=contract.freshness_state,
                    trust_state=self._trust_from_freshness(contract.freshness_state),
                )
            if content.release_process_reference:
                key = f"{contract.project_id}:release:{content.release_process_reference}"
                validations[key] = ChangeImpactValidationReference(
                    validation_id=_deterministic_id(
                        "change-impact-validation",
                        {"project_id": contract.project_id, "kind": "release_process_reference", "reference": content.release_process_reference},
                    ),
                    project_id=contract.project_id,
                    reference_kind="release_process_reference",
                    reference=content.release_process_reference,
                    description=f"Release process reference for {contract.project_id}.",
                    source_contract_id=contract.contract_id,
                    source_contract_revision_id=contract.current_revision_id,
                    freshness_state=contract.freshness_state,
                    trust_state=self._trust_from_freshness(contract.freshness_state),
                )
        if not validations and target_resolutions:
            return [
                ChangeImpactValidationReference(
                    validation_id=_deterministic_id("change-impact-validation", {"kind": "insufficient_test_metadata", "proposal_targets": [item.target_id for item in target_resolutions]}),
                    project_id=target_resolutions[0].resolved_project_id or target_resolutions[0].target_id,
                    reference_kind="test_command",
                    reference="unknown",
                    description="No canonical test or build commands were available for the affected scope.",
                    freshness_state="unknown",
                    trust_state="unknown",
                    details={"reason": "insufficient_test_metadata"},
                )
            ]
        return sorted(validations.values(), key=lambda item: (item.project_id, item.reference_kind, item.reference))

    def _collect_refresh_requirements(
        self,
        proposal: ChangeProposal,
        target_resolutions: list[ChangeImpactTargetResolution],
        direct_entities: list[ChangeImpactEntityRecord],
        transitive_entities: list[ChangeImpactEntityRecord],
        affected_contracts: list[ChangeImpactContractRecord],
        affected_releases: list[ChangeImpactReleaseRecord],
        affected_work_packages: list[ChangeImpactWorkPackageRecord],
    ) -> list[ChangeImpactRefreshRequirement]:
        requirements: dict[str, ChangeImpactRefreshRequirement] = {}
        for resolution in target_resolutions:
            if resolution.resolution_state != "resolved":
                requirement = ChangeImpactRefreshRequirement(
                    refresh_requirement_id=_deterministic_id(
                        "change-impact-refresh",
                        {"subject_kind": "proposal", "subject_id": proposal.proposal_id, "target_id": resolution.target_id},
                    ),
                    subject_kind="proposal",
                    subject_id=proposal.proposal_id,
                    refresh_kind="resolve_target",
                    reason_code="UNKNOWN_TARGET",
                    description=f"Target {resolution.target_id} could not be resolved canonically.",
                    freshness_state=resolution.freshness_state,
                    trust_state=resolution.trust_state,
                    details=resolution.details,
                )
                requirements[requirement.refresh_requirement_id] = requirement
        for entity in [*direct_entities, *transitive_entities]:
            if entity.freshness_state in {"stale", "unknown", "unavailable"}:
                requirement = ChangeImpactRefreshRequirement(
                    refresh_requirement_id=_deterministic_id("change-impact-refresh", {"subject_kind": "entity", "subject_id": entity.node_id, "freshness": entity.freshness_state}),
                    subject_kind="entity",
                    subject_id=entity.node_id,
                    refresh_kind="refresh_dependency_evidence",
                    reason_code="STALE_EVIDENCE" if entity.freshness_state == "stale" else "UNVERIFIED_CONTRACT_IMPACT",
                    description=f"Entity evidence for {entity.node_id} is not current enough for a fully trusted impact result.",
                    freshness_state=entity.freshness_state,
                    trust_state=entity.trust_state,
                    details={"entity_kind": entity.entity_kind, "owning_project_or_domain": entity.owning_project_or_domain},
                )
                requirements[requirement.refresh_requirement_id] = requirement
        for contract in affected_contracts:
            if contract.freshness_state in {"stale", "unknown", "unavailable"}:
                requirement = ChangeImpactRefreshRequirement(
                    refresh_requirement_id=_deterministic_id("change-impact-refresh", {"subject_kind": "contract", "subject_id": contract.contract_id, "freshness": contract.freshness_state}),
                    subject_kind="contract",
                    subject_id=contract.contract_id,
                    refresh_kind="refresh_project_contract",
                    reason_code="STALE_EVIDENCE" if contract.freshness_state == "stale" else "MISSING_CONTRACT",
                    description=f"Contract evidence for {contract.contract_id} needs to be refreshed.",
                    freshness_state=contract.freshness_state,
                    trust_state=contract.trust_state,
                    details={"project_id": contract.project_id},
                )
                requirements[requirement.refresh_requirement_id] = requirement
        if not requirements and not affected_work_packages:
            requirements[_deterministic_id("change-impact-refresh", {"subject_kind": "graph", "subject_id": proposal.proposal_id})] = ChangeImpactRefreshRequirement(
                refresh_requirement_id=_deterministic_id("change-impact-refresh", {"subject_kind": "graph", "subject_id": proposal.proposal_id}),
                subject_kind="graph",
                subject_id=proposal.proposal_id,
                refresh_kind="refresh_change_evidence",
                reason_code="INSUFFICIENT_EVIDENCE",
                description="The analysis did not find enough canonical evidence to treat the proposal as fully verified.",
                freshness_state="unknown",
                trust_state="unknown",
            )
        return sorted(requirements.values(), key=lambda item: (item.subject_kind, item.subject_id, item.refresh_kind))

    def _collect_sequencing_constraints(
        self,
        direct_entities: list[ChangeImpactEntityRecord],
        target_resolutions: list[ChangeImpactTargetResolution],
    ) -> list[ChangeImpactSequencingConstraint]:
        constraints: dict[str, ChangeImpactSequencingConstraint] = {}
        for entity in direct_entities:
            if entity.owning_project_or_domain is None:
                continue
            for resolution in target_resolutions:
                if resolution.resolved_project_id is None:
                    continue
                if resolution.resolved_project_id == entity.owning_project_or_domain:
                    continue
                constraint = ChangeImpactSequencingConstraint(
                    sequencing_constraint_id=_deterministic_id(
                        "change-impact-sequencing",
                        {
                            "prerequisite_project_id": resolution.resolved_project_id,
                            "dependent_project_id": entity.owning_project_or_domain,
                            "entity_id": entity.node_id,
                        },
                    ),
                    prerequisite_project_id=resolution.resolved_project_id,
                    prerequisite_entity_id=resolution.resolved_entity_id,
                    dependent_project_id=entity.owning_project_or_domain,
                    dependent_entity_id=entity.node_id,
                    reason_code="DIRECT_CONSUMER" if entity.impact_scope == "direct" else "TRANSITIVE_DEPENDENT",
                    description=f"{resolution.resolved_project_id} should be updated before validating {entity.owning_project_or_domain}.",
                    supporting_node_ids=[entity.node_id],
                    supporting_edge_ids=list(entity.path_edge_ids),
                    provenance_references=entity.provenance_references,
                    freshness_state=entity.freshness_state,
                    trust_state=entity.trust_state,
                )
                constraints[constraint.sequencing_constraint_id] = constraint
        return sorted(constraints.values(), key=lambda item: item.sequencing_constraint_id)

    def _collect_unknown_findings(
        self,
        proposal: ChangeProposal,
        target_resolutions: list[ChangeImpactTargetResolution],
        affected_contracts: list[ChangeImpactContractRecord],
        validation_references: list[ChangeImpactValidationReference],
        affected_work_packages: list[ChangeImpactWorkPackageRecord],
        graph: DependencyGraphSnapshot,
    ) -> list[ChangeImpactFinding]:
        findings: dict[str, ChangeImpactFinding] = {}
        for resolution in target_resolutions:
            if resolution.resolution_state == "resolved":
                continue
            findings[resolution.resolution_id] = ChangeImpactFinding(
                finding_id=resolution.resolution_id,
                finding_type="UNKNOWN_TARGET",
                severity="critical",
                summary=f"Target {resolution.target_id} could not be resolved.",
                explanation="The proposed change references a target that is not canonical in the current registry state.",
                affected_project_id=resolution.resolved_project_id,
                related_target_ids=[resolution.target_id],
                provenance_references=resolution.provenance_references,
                freshness_state=resolution.freshness_state,
                trust_state=resolution.trust_state,
                details=resolution.details,
            )
        if not affected_contracts and proposal.change_type == "PROJECT_CONTRACT_CHANGE":
            findings[_deterministic_id("change-impact-finding", {"type": "missing_contract", "proposal": proposal.proposal_id})] = ChangeImpactFinding(
                finding_id=_deterministic_id("change-impact-finding", {"type": "missing_contract", "proposal": proposal.proposal_id}),
                finding_type="MISSING_CONTRACT",
                severity="critical",
                summary="No canonical project contract was available for the proposed change.",
                explanation="The change proposal targets a contract change, but there is no approved canonical contract to analyse against.",
                freshness_state="unavailable",
                trust_state="unavailable",
                details={"proposal_id": proposal.proposal_id},
            )
        if not validation_references:
            findings[_deterministic_id("change-impact-finding", {"type": "insufficient_test_metadata", "proposal": proposal.proposal_id})] = ChangeImpactFinding(
                finding_id=_deterministic_id("change-impact-finding", {"type": "insufficient_test_metadata", "proposal": proposal.proposal_id}),
                finding_type="INSUFFICIENT_TEST_METADATA",
                severity="warning",
                summary="No canonical validation metadata was available.",
                explanation="The impacted scope does not expose canonical test or build commands in the current contract state.",
                freshness_state="unknown",
                trust_state="unknown",
                details={"proposal_id": proposal.proposal_id},
            )
        if not affected_work_packages and proposal.target_entities:
            findings[_deterministic_id("change-impact-finding", {"type": "insufficient_work_package_linkage", "proposal": proposal.proposal_id})] = ChangeImpactFinding(
                finding_id=_deterministic_id("change-impact-finding", {"type": "insufficient_work_package_linkage", "proposal": proposal.proposal_id}),
                finding_type="INSUFFICIENT_WORK_PACKAGE_LINKAGE",
                severity="warning",
                summary="No canonical work-package linkage could be proven for the affected scope.",
                explanation="The current work-package records do not expose enough canonical linkage to prove overlap beyond project identity.",
                freshness_state="unknown",
                trust_state="unknown",
                details={"proposal_id": proposal.proposal_id},
            )
        for finding in graph.findings:
            if finding.finding_type in {"unresolved_dependency", "missing_contract", "conflict", "unsupported_dependency"}:
                findings[finding.finding_id] = ChangeImpactFinding(
                    finding_id=finding.finding_id,
                    finding_type="UNRESOLVED_DEPENDENCY" if finding.finding_type == "unresolved_dependency" else "CONFLICTING_RELATIONSHIPS" if finding.finding_type == "conflict" else "UNVERIFIED_CONTRACT_IMPACT" if finding.finding_type == "unsupported_dependency" else "MISSING_CONTRACT",
                    severity=finding.severity,
                    summary=finding.summary,
                    explanation=finding.explanation,
                    affected_project_id=finding.root_project_id,
                    affected_entity_id=finding.root_entity_id,
                    related_target_ids=[],
                    related_node_ids=finding.related_node_ids,
                    related_edge_ids=finding.related_edge_ids,
                    provenance_references=finding.provenance_references,
                    freshness_state=finding.freshness_state,
                    trust_state=finding.trust_state,
                    details=finding.details,
                )
        return sorted(findings.values(), key=lambda item: (item.finding_type, item.severity, item.finding_id))

    def _calculate_risk(
        self,
        proposal: ChangeProposal,
        direct_entities: list[ChangeImpactEntityRecord],
        transitive_entities: list[ChangeImpactEntityRecord],
        affected_projects: list[ChangeImpactProjectRecord],
        affected_contracts: list[ChangeImpactContractRecord],
        affected_releases: list[ChangeImpactReleaseRecord],
        affected_work_packages: list[ChangeImpactWorkPackageRecord],
        validation_references: list[ChangeImpactValidationReference],
        refresh_requirements: list[ChangeImpactRefreshRequirement],
        sequencing_constraints: list[ChangeImpactSequencingConstraint],
        unknown_findings: list[ChangeImpactFinding],
        graph: DependencyGraphSnapshot,
    ) -> ChangeImpactRiskResult:
        factors: list[ChangeImpactRiskFactor] = []
        score = 0

        def add_factor(factor_id: str, description: str, value: int, weight: int, evidence_ids: list[str] | None = None, details: dict[str, Any] | None = None) -> None:
            nonlocal score
            contribution = value * weight
            score += contribution
            factors.append(
                ChangeImpactRiskFactor(
                    factor_id=factor_id,
                    description=description,
                    value=value,
                    weight=weight,
                    contribution=contribution,
                    evidence_ids=evidence_ids or [],
                    details=details or {},
                )
            )

        add_factor("direct_entities", "Directly affected entities.", len(direct_entities), 4)
        add_factor("transitive_entities", "Transitively affected entities.", len(transitive_entities), 2)
        add_factor("affected_projects", "Affected projects.", max(0, len(affected_projects) - 1), 3)
        add_factor("affected_contracts", "Affected canonical contracts.", len(affected_contracts), 3)
        add_factor("affected_releases", "Affected release records.", len(affected_releases), 2)
        add_factor("affected_work_packages", "Potentially impacted work packages.", len(affected_work_packages), 2)
        add_factor("validation_references", "Relevant validation references.", len(validation_references), -1)
        add_factor("refresh_requirements", "Evidence refresh requirements.", len(refresh_requirements), 3)
        add_factor("sequencing_constraints", "Sequencing constraints.", len(sequencing_constraints), 2)
        add_factor("unknown_findings", "Unknown or unverified findings.", len(unknown_findings), 5)
        add_factor("cycle_involvement", "Dependency graph cycle involvement.", len([finding for finding in graph.findings if finding.finding_type == "cycle"]), 4)
        add_factor("shared_dependencies", "Shared dependency breadth.", len([finding for finding in graph.findings if finding.finding_type == "shared_dependency"]), 2)
        add_factor("unresolved_dependencies", "Unresolved dependency findings.", len([finding for finding in graph.findings if finding.finding_type == "unresolved_dependency"]), 4)
        critical_projects = 0
        for contract in affected_contracts:
            current_contract = self._current_contract_for_project(contract.project_id)
            if current_contract is None or current_contract.current_revision is None:
                continue
            criticality = current_contract.current_revision.content.criticality
            critical_projects += {"low": 0, "medium": 1, "high": 2, "critical": 3, "unknown": 1}.get(criticality, 1)
        add_factor("project_criticality", "Criticality of affected project contracts.", critical_projects, 2)

        if not direct_entities and not transitive_entities and all(item.freshness_state in {"unknown", "unavailable"} for item in unknown_findings):
            level: ChangeImpactRiskLevel = "UNKNOWN"
        elif score <= 3:
            level = "LOW"
        elif score <= 10:
            level = "MEDIUM"
        elif score <= 18:
            level = "HIGH"
        else:
            level = "CRITICAL"

        if unknown_findings and level == "LOW":
            level = "MEDIUM"
        if any(finding.finding_type in {"UNKNOWN_TARGET", "MISSING_CONTRACT", "CONFLICTING_RELATIONSHIPS"} for finding in unknown_findings) and level == "UNKNOWN":
            level = "MEDIUM"

        factor_codes = [factor.factor_id for factor in factors]
        evidence_fingerprints = [proposal.proposal_id, graph.graph_fingerprint]
        explanation = "Risk is derived deterministically from the number, breadth and evidentiary quality of direct and transitive impacts."
        return ChangeImpactRiskResult(
            risk_level=level,
            score=score,
            factor_codes=factor_codes,
            factors=factors,
            evidence_fingerprints=_dedupe_preserve_order(evidence_fingerprints),
            explanation=explanation,
            details={"proposal_id": proposal.proposal_id, "change_type": proposal.change_type},
        )

    def _impact_payload(self, result: ChangeImpactResult) -> dict[str, Any]:
        return {
            "proposal_revision_fingerprint": result.proposal_revision_fingerprint,
            "proposal_identity_fingerprint": result.proposal_identity_fingerprint,
            "graph_fingerprint": result.graph_fingerprint,
            "target_resolutions": [self._fingerprint_model(item) for item in result.target_resolutions],
            "direct_entities": [self._fingerprint_model(item) for item in result.direct_entities],
            "transitive_entities": [self._fingerprint_model(item) for item in result.transitive_entities],
            "affected_projects": [self._fingerprint_model(item) for item in result.affected_projects],
            "affected_contracts": [self._fingerprint_model(item) for item in result.affected_contracts],
            "affected_releases": [self._fingerprint_model(item) for item in result.affected_releases],
            "affected_work_packages": [self._fingerprint_model(item) for item in result.affected_work_packages],
            "validation_references": [self._fingerprint_model(item) for item in result.validation_references],
            "refresh_requirements": [self._fingerprint_model(item) for item in result.refresh_requirements],
            "sequencing_constraints": [self._fingerprint_model(item) for item in result.sequencing_constraints],
            "unknown_findings": [self._fingerprint_model(item) for item in result.unknown_findings],
            "risk": self._fingerprint_model(result.risk),
            "freshness_state": result.freshness_state,
            "trust_state": result.trust_state,
        }

    def _fingerprint_model(self, model: BaseModel) -> dict[str, Any]:
        return cast(dict[str, Any], self._stable_fingerprint_value(json.loads(model.model_dump_json())))

    def _proposal_identity_fingerprint(self, proposal: ChangeProposal) -> str:
        payload = {
            "title": proposal.title,
            "origin_project": proposal.origin_project,
            "objective": proposal.objective,
            "change_type": proposal.change_type,
            "target_entities": [item.model_dump(mode="json") for item in proposal.target_entities],
            "proposed_contract_changes": self._normalise_value(proposal.proposed_contract_changes),
        }
        return _content_fingerprint(payload)

    def _proposal_revision_fingerprint(self, proposal: ChangeProposal) -> str:
        return _content_fingerprint(self._fingerprint_model(proposal))

    def _proposal_id(self, proposal: ChangeProposal) -> str:
        return _deterministic_id("change-proposal", {"proposal_identity_fingerprint": self._proposal_identity_fingerprint(proposal)})

    def _project(self, project_id: str) -> ProjectConfig:
        try:
            return self.settings.projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def _resolve_contract_target(self, target_id: str) -> ProjectContractRecord | None:
        contract = self.project_contract_service.current_approved_contract(target_id)
        if contract is not None:
            return contract
        return self.database.get_project_contract_by_id(target_id)

    def _resolve_entity_target(
        self,
        target_id: str,
        entity_index: dict[str, ArchitectureEntityRecord],
        entity_index_by_identity: dict[str, ArchitectureEntityRecord],
        target_kind: ChangeProposalTargetKind,
    ) -> ArchitectureEntityRecord | None:
        entity = entity_index.get(target_id) or entity_index_by_identity.get(target_id)
        if entity is not None:
            return entity
        if target_kind in {"api_contract", "schema", "release_contract", "data_contract", "protocol_contract", "package", "library", "hardware"}:
            for candidate in entity_index.values():
                if candidate.identity_key == target_id or candidate.name == target_id:
                    return candidate
        return None

    def _resolve_reference(self, reference: str) -> ArchitectureEntityRecord | None:
        entities = self.architecture_registry_service.list_entities()
        by_id = {entity.entity_id: entity for entity in entities}
        by_identity = {entity.identity_key: entity for entity in entities}
        return by_id.get(reference) or by_identity.get(reference)

    def _contract_declarations(self, content: ProjectContractContent) -> list[dict[str, Any]]:
        declarations: list[dict[str, Any]] = []
        for reference in content.dependencies:
            declarations.append({"field": "dependencies", "reference": reference, "relationship_type": "DEPENDS_ON"})
        for reference in content.shared_packages:
            declarations.append({"field": "shared_packages", "reference": reference, "relationship_type": "USES_PACKAGE"})
        for reference in content.hardware_dependencies:
            declarations.append({"field": "hardware_dependencies", "reference": reference, "relationship_type": "DEPENDS_ON"})
        for reference in content.data_contracts:
            declarations.append({"field": "data_contracts", "reference": reference, "relationship_type": "CONSUMES_DATA_FROM"})
        for reference in content.api_contracts:
            declarations.append({"field": "api_contracts", "reference": reference, "relationship_type": "CONSUMES_API_FROM"})
        for reference in content.architecture_references:
            declarations.append({"field": "architecture_references", "reference": reference, "relationship_type": "VALIDATES"})
        if content.release_process_reference:
            declarations.append({"field": "release_process_reference", "reference": content.release_process_reference, "relationship_type": "RELEASES_WITH"})
        return declarations

    def _current_contract_for_project(self, project_id: str) -> ProjectContractRecord | None:
        return self.project_contract_service.current_approved_contract(project_id)

    def _node_by_id(self, nodes: list[DependencyGraphNode], node_id: str) -> DependencyGraphNode | None:
        for node in nodes:
            if node.node_id == node_id:
                return node
        return None

    def _impact_entity_from_node(
        self,
        node: DependencyGraphNode,
        *,
        impact_scope: ChangeImpactScope,
        reason_codes: list[ChangeImpactReasonCode],
        path_node_ids: list[str],
        path_edge_ids: list[str],
        supporting_target_ids: list[str],
        provenance_references: list[ProgrammeProvenanceRecord],
        freshness_state: str,
        trust_state: str,
        details: dict[str, Any],
    ) -> ChangeImpactEntityRecord:
        return ChangeImpactEntityRecord(
            impact_id=_deterministic_id(
                "change-impact-entity",
                {
                    "node_id": node.node_id,
                    "impact_scope": impact_scope,
                    "reason_codes": reason_codes,
                    "path_node_ids": path_node_ids,
                    "path_edge_ids": path_edge_ids,
                },
            ),
            impact_scope=impact_scope,
            node_id=node.node_id,
            architecture_entity_id=node.architecture_entity_id,
            entity_kind=node.entity_kind,
            owning_project_or_domain=node.owning_project_or_domain,
            reason_codes=_dedupe_preserve_order(reason_codes),
            path_node_ids=_dedupe_preserve_order(path_node_ids),
            path_edge_ids=_dedupe_preserve_order(path_edge_ids),
            supporting_target_ids=_dedupe_preserve_order(supporting_target_ids),
            provenance_references=_dedupe_provenance(provenance_references),
            freshness_state=freshness_state,
            trust_state=trust_state,
            details=details,
        )

    def _impact_entity_from_dependency(
        self,
        record: DependencyGraphDependencyRecord,
        *,
        impact_scope: ChangeImpactScope,
        reason_code: ChangeImpactReasonCode,
        supporting_target_ids: list[str],
    ) -> ChangeImpactEntityRecord:
        return ChangeImpactEntityRecord(
            impact_id=_deterministic_id(
                "change-impact-entity",
                {
                    "node_id": record.node_id,
                    "impact_scope": impact_scope,
                    "reason_code": reason_code,
                    "path_node_ids": record.path_node_ids,
                    "path_edge_ids": record.path_edge_ids,
                },
            ),
            impact_scope=impact_scope,
            node_id=record.node_id,
            architecture_entity_id=record.architecture_entity_id,
            entity_kind=record.entity_kind,
            owning_project_or_domain=record.owning_project_or_domain,
            reason_codes=_dedupe_preserve_order([reason_code, *[self._reason_code_for_relationship_type(item) for item in record.relationship_types]]),
            path_node_ids=record.path_node_ids,
            path_edge_ids=record.path_edge_ids,
            supporting_target_ids=_dedupe_preserve_order(supporting_target_ids),
            provenance_references=record.provenance_references,
            freshness_state=record.freshness_state,
            trust_state=record.trust_state,
            details={"declared_reference": record.declared_reference, "version_constraint": record.version_constraint, "contract_constraint": record.contract_constraint},
        )

    def _reason_code_for_dependency(self, target_kind: ChangeProposalTargetKind, record: DependencyGraphDependencyRecord) -> ChangeImpactReasonCode:
        if target_kind == "project_contract":
            return "CONTRACT_CONSUMER"
        if target_kind in {"schema", "data_contract"}:
            return "SCHEMA_CONSUMER"
        if target_kind in {"release_contract", "project"}:
            return "RELEASE_COUPLING"
        if target_kind in {"api_contract", "protocol_contract"}:
            return "CONTRACT_CONSUMER"
        return "DIRECT_CONSUMER"

    def _reason_code_for_relationship_type(self, relationship_type: str) -> ChangeImpactReasonCode:
        return cast(
            ChangeImpactReasonCode,
            {
            "CONSUMES_API_FROM": "CONTRACT_CONSUMER",
            "CONSUMES_DATA_FROM": "SCHEMA_CONSUMER",
            "RELEASES_WITH": "RELEASE_COUPLING",
            }.get(relationship_type, "DIRECT_CONSUMER"),
        )

    def _merge_entity_impact(self, container: dict[str, ChangeImpactEntityRecord], record: ChangeImpactEntityRecord) -> None:
        existing = container.get(record.node_id)
        if existing is None:
            container[record.node_id] = record
            return
        container[record.node_id] = existing.model_copy(
            update={
                "impact_scope": "direct" if existing.impact_scope == "direct" or record.impact_scope == "direct" else "transitive",
                "reason_codes": _dedupe_preserve_order([*existing.reason_codes, *record.reason_codes]),
                "path_node_ids": _dedupe_preserve_order([*existing.path_node_ids, *record.path_node_ids]),
                "path_edge_ids": _dedupe_preserve_order([*existing.path_edge_ids, *record.path_edge_ids]),
                "supporting_target_ids": _dedupe_preserve_order([*existing.supporting_target_ids, *record.supporting_target_ids]),
                "provenance_references": _dedupe_provenance([*existing.provenance_references, *record.provenance_references]),
                "freshness_state": self._merge_freshness(existing.freshness_state, record.freshness_state),
                "trust_state": self._combine_trust([existing.trust_state, record.trust_state]),
                "details": {**existing.details, **record.details},
            }
        )

    def _merge_project_impact(self, container: dict[str, ChangeImpactProjectRecord], record: ChangeImpactProjectRecord) -> None:
        existing = container.get(record.project_id)
        if existing is None:
            container[record.project_id] = record
            return
        container[record.project_id] = existing.model_copy(
            update={
                "impact_scope": "direct" if existing.impact_scope == "direct" or record.impact_scope == "direct" else "transitive",
                "supporting_entity_ids": _dedupe_preserve_order([*existing.supporting_entity_ids, *record.supporting_entity_ids]),
                "supporting_edge_ids": _dedupe_preserve_order([*existing.supporting_edge_ids, *record.supporting_edge_ids]),
                "supporting_target_ids": _dedupe_preserve_order([*existing.supporting_target_ids, *record.supporting_target_ids]),
                "path_node_ids": _dedupe_preserve_order([*existing.path_node_ids, *record.path_node_ids]),
                "path_edge_ids": _dedupe_preserve_order([*existing.path_edge_ids, *record.path_edge_ids]),
                "reason_codes": _dedupe_preserve_order([*existing.reason_codes, *record.reason_codes]),
                "provenance_references": _dedupe_provenance([*existing.provenance_references, *record.provenance_references]),
                "freshness_state": self._merge_freshness(existing.freshness_state, record.freshness_state),
                "trust_state": self._combine_trust([existing.trust_state, record.trust_state]),
                "details": {**existing.details, **record.details},
            }
        )

    def _merge_contract_impact(self, container: dict[str, ChangeImpactContractRecord], record: ChangeImpactContractRecord) -> None:
        existing = container.get(record.contract_id)
        if existing is None:
            container[record.contract_id] = record
            return
        container[record.contract_id] = existing.model_copy(
            update={
                "impact_scope": "direct" if existing.impact_scope == "direct" or record.impact_scope == "direct" else "transitive",
                "reason_codes": _dedupe_preserve_order([*existing.reason_codes, *record.reason_codes]),
                "provenance_references": _dedupe_provenance([*existing.provenance_references, *record.provenance_references]),
                "freshness_state": self._merge_freshness(existing.freshness_state, record.freshness_state),
                "trust_state": self._combine_trust([existing.trust_state, record.trust_state]),
                "details": {**existing.details, **record.details},
            }
        )

    def _merge_release_impact(self, container: dict[str, ChangeImpactReleaseRecord], record: ChangeImpactReleaseRecord) -> None:
        existing = container.get(record.project_id)
        if existing is None:
            container[record.project_id] = record
            return
        container[record.project_id] = existing.model_copy(
            update={
                "impact_scope": "direct" if existing.impact_scope == "direct" or record.impact_scope == "direct" else "transitive",
                "reason_codes": _dedupe_preserve_order([*existing.reason_codes, *record.reason_codes]),
                "provenance_references": _dedupe_provenance([*existing.provenance_references, *record.provenance_references]),
                "freshness_state": self._merge_freshness(existing.freshness_state, record.freshness_state),
                "trust_state": self._combine_trust([existing.trust_state, record.trust_state]),
                "details": {**existing.details, **record.details},
            }
        )

    def _collect_work_package_overlap(self, package: WorkPackageRecord, target_ids: set[str]) -> bool:
        evidence_tokens = {
            *package.source_finding_ids,
            *package.source_comparison_ids,
            *package.source_snapshot_ids,
            *package.evidence_fingerprints,
            package.source_recommendation_id,
        }
        return bool(target_ids & evidence_tokens)

    def _work_package_overlaps_targets(self, package: WorkPackageRecord, target_ids: set[str]) -> bool:
        if self._collect_work_package_overlap(package, target_ids):
            return True
        return False

    def _combine_freshness(self, values: list[str]) -> str:
        if not values:
            return "unknown"
        if "unavailable" in values:
            return "unavailable"
        if "stale" in values:
            return "stale"
        if "unknown" in values:
            return "unknown"
        return "fresh"

    def _combine_trust(self, values: list[str]) -> str:
        if not values:
            return "unknown"
        order = {"trusted": 4, "trusted_with_warning": 3, "partial": 2, "stale": 1, "unknown": 0, "conflicting": -1, "unavailable": -2}
        return min(values, key=lambda item: order.get(item, 0))

    def _trust_from_freshness(self, freshness: str) -> str:
        return {"fresh": "trusted", "stale": "stale", "unknown": "unknown", "unavailable": "unavailable"}.get(freshness, "unknown")

    def _merge_freshness(self, left: str, right: str) -> str:
        if "unavailable" in {left, right}:
            return "unavailable"
        if "stale" in {left, right}:
            return "stale"
        if "unknown" in {left, right}:
            return "unknown"
        return "fresh"

    def _normalise_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return cast(dict[str, Any], {key: self._normalise_value(value[key]) for key in sorted(value)})
        if isinstance(value, list):
            return [self._normalise_value(item) for item in value]
        return value

    def _stable_fingerprint_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._stable_fingerprint_value(item)
                for key, item in sorted(value.items())
                if key not in {"captured_at", "audit_event_id", "event_id"}
            }
        if isinstance(value, list):
            return [self._stable_fingerprint_value(item) for item in value]
        return value

    def _proposal_provenance(self, proposal: ChangeProposal) -> list[ProgrammeProvenanceRecord]:
        return [
            ProgrammeProvenanceRecord(
                source_project_id=proposal.origin_project,
                canonical_gaia_source="proposal",
                details={"proposal_id": proposal.proposal_id, "revision": proposal.revision, "change_type": proposal.change_type},
            )
        ]

    def _graph_provenance(self, graph: DependencyGraphSnapshot) -> list[ProgrammeProvenanceRecord]:
        return [
            ProgrammeProvenanceRecord(
                canonical_gaia_source="dependency-graph",
                details={
                    "graph_id": graph.graph_id,
                    "graph_fingerprint": graph.graph_fingerprint,
                    "node_count": graph.node_count,
                    "edge_count": graph.edge_count,
                },
            )
        ]


def _dedupe_preserve_order(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    ordered: list[Any] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _dedupe_provenance(values: list[ProgrammeProvenanceRecord]) -> list[ProgrammeProvenanceRecord]:
    seen: set[str] = set()
    ordered: list[ProgrammeProvenanceRecord] = []
    for value in values:
        payload = value.model_dump(mode="json")
        fingerprint = _content_fingerprint(payload)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        ordered.append(value)
    return ordered


def _content_fingerprint(value: Any) -> str:
    payload = json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _deterministic_id(namespace: str, payload: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"gaia:{namespace}:{_content_fingerprint(payload)}"))


def _dedupe_target_resolutions(values: list[ChangeImpactTargetResolution]) -> list[ChangeImpactTargetResolution]:
    by_id: dict[str, ChangeImpactTargetResolution] = {}
    for value in values:
        existing = by_id.get(value.resolution_id)
        if existing is None:
            by_id[value.resolution_id] = value
            continue
        by_id[value.resolution_id] = existing.model_copy(
            update={
                "resolution_state": "resolved" if "resolved" in {existing.resolution_state, value.resolution_state} else existing.resolution_state,
                "resolved_project_id": existing.resolved_project_id or value.resolved_project_id,
                "resolved_entity_id": existing.resolved_entity_id or value.resolved_entity_id,
                "resolved_contract_id": existing.resolved_contract_id or value.resolved_contract_id,
                "resolved_work_package_id": existing.resolved_work_package_id or value.resolved_work_package_id,
                "resolved_node_id": existing.resolved_node_id or value.resolved_node_id,
                "resolved_label": existing.resolved_label or value.resolved_label,
                "provenance_references": _dedupe_provenance([*existing.provenance_references, *value.provenance_references]),
                "freshness_state": value.freshness_state if value.freshness_state != "unknown" else existing.freshness_state,
                "trust_state": value.trust_state if value.trust_state != "unknown" else existing.trust_state,
                "details": {**existing.details, **value.details},
            }
        )
    return sorted(by_id.values(), key=lambda item: (item.target_kind, item.target_id, item.resolution_id))
