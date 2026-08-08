from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gaia.config import Settings
from gaia.models import ProjectConfig, utc_now
from gaia.programme_registry import (
    ArchitectureEntityKind,
    ArchitectureEntityRecord,
    ArchitectureRegistryService,
    ArchitectureRelationshipRecord,
    ArchitectureRelationshipType,
    EvidenceFreshnessState,
    ProgrammeProvenanceRecord,
    ProjectContractContent,
    ProjectContractRecord,
    ProjectContractService,
)

DependencyGraphTrustState = Literal[
    "trusted",
    "trusted_with_warning",
    "partial",
    "stale",
    "unknown",
    "conflicting",
    "unavailable",
]

DependencyGraphFindingType = Literal[
    "unresolved_dependency",
    "missing_contract",
    "unsupported_dependency",
    "cycle",
    "shared_dependency",
    "orphan",
    "conflict",
]


class DependencyGraphNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    node_id: str
    architecture_entity_id: str
    entity_kind: ArchitectureEntityKind
    owning_project_or_domain: str | None = None
    current_entity_revision_id: str | None = None
    status: str = "draft"
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"
    current_contract_revision_id: str | None = None


class DependencyGraphEdge(BaseModel):
    model_config = ConfigDict(extra="ignore")

    edge_id: str
    source_node_id: str
    target_node_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: ArchitectureRelationshipType
    canonical_relationship_reference: str
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"
    version_constraint: str | None = None
    contract_constraint: dict[str, Any] | None = None
    source_revision_id: str | None = None
    target_revision_id: str | None = None
    declared_reference: str | None = None


class DependencyGraphDependencyRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dependency_id: str
    root_node_id: str
    node_id: str
    architecture_entity_id: str
    entity_kind: ArchitectureEntityKind
    owning_project_or_domain: str | None = None
    depth: int = Field(ge=1)
    path_node_ids: list[str] = Field(default_factory=list)
    path_edge_ids: list[str] = Field(default_factory=list)
    relationship_types: list[ArchitectureRelationshipType] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"
    declared_reference: str | None = None
    contract_constraint: dict[str, Any] | None = None
    version_constraint: str | None = None

    @field_validator("path_node_ids", "path_edge_ids", "relationship_types")
    @classmethod
    def _normalise_lists(cls, values: list[Any]) -> list[Any]:
        return _dedupe_preserve_order([str(value) for value in values])


class DependencyGraphProjectDependencyRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_dependency_id: str
    source_project_id: str
    target_project_id: str
    source_project_node_id: str
    target_project_node_id: str
    representative_dependency_id: str
    representative_path_node_ids: list[str] = Field(default_factory=list)
    representative_path_edge_ids: list[str] = Field(default_factory=list)
    supporting_node_ids: list[str] = Field(default_factory=list)
    supporting_edge_ids: list[str] = Field(default_factory=list)
    relationship_types: list[ArchitectureRelationshipType] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"
    declared_references: list[str] = Field(default_factory=list)
    contract_constraints: list[dict[str, Any]] = Field(default_factory=list)
    version_constraints: list[str] = Field(default_factory=list)


class DependencyGraphCycleRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cycle_id: str
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=list)
    relationship_types: list[ArchitectureRelationshipType] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class DependencyGraphSharedDependencyRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shared_dependency_id: str
    node_id: str
    architecture_entity_id: str
    entity_kind: ArchitectureEntityKind
    owning_project_or_domain: str | None = None
    dependent_node_ids: list[str] = Field(default_factory=list)
    dependent_project_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    relationship_types: list[ArchitectureRelationshipType] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class DependencyGraphOrphanRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    orphan_id: str
    node_id: str
    architecture_entity_id: str
    entity_kind: ArchitectureEntityKind
    owning_project_or_domain: str | None = None
    reason: str
    provenance: ProgrammeProvenanceRecord
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"


class DependencyGraphFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")

    finding_id: str
    finding_type: DependencyGraphFindingType
    severity: Literal["info", "warning", "critical"] = "warning"
    summary: str
    explanation: str
    root_project_id: str | None = None
    root_entity_id: str | None = None
    related_node_ids: list[str] = Field(default_factory=list)
    related_edge_ids: list[str] = Field(default_factory=list)
    provenance_references: list[ProgrammeProvenanceRecord] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class DependencyGraphSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    graph_id: str
    graph_fingerprint: str
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    source_contract_revision_ids: list[str] = Field(default_factory=list)
    source_entity_revision_ids: list[str] = Field(default_factory=list)
    source_relationship_revision_ids: list[str] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    nodes: list[DependencyGraphNode] = Field(default_factory=list)
    edges: list[DependencyGraphEdge] = Field(default_factory=list)
    findings: list[DependencyGraphFinding] = Field(default_factory=list)
    freshness_state: EvidenceFreshnessState = "unknown"
    trust_state: DependencyGraphTrustState = "unknown"


class DependencyGraphService:
    def __init__(
        self,
        settings: Settings,
        project_contract_service: ProjectContractService,
        architecture_registry_service: ArchitectureRegistryService,
    ) -> None:
        self.settings = settings
        self.project_contract_service = project_contract_service
        self.architecture_registry_service = architecture_registry_service

    def build_graph(self) -> DependencyGraphSnapshot:
        projects = [self.settings.projects[project_id] for project_id in sorted(self.settings.projects)]
        current_contracts = self._current_contracts(projects)
        entities = self._current_entities()
        relationships = self._current_relationships()

        nodes = [self._node_from_entity(entity, current_contracts.get(entity.identity_key)) for entity in entities]
        node_map = {node.node_id: node for node in nodes}
        entity_map = {entity.entity_id: entity for entity in entities}
        identity_key_map = {entity.identity_key: entity for entity in entities}

        edges: list[DependencyGraphEdge] = []
        findings: list[DependencyGraphFinding] = []
        architecture_support_pairs: set[tuple[str, str]] = set()

        for relationship in relationships:
            source = entity_map.get(relationship.source_entity_id)
            target = entity_map.get(relationship.target_entity_id)
            if source is None or target is None:
                findings.append(
                    self._finding(
                        finding_type="conflict",
                        severity="critical",
                        summary="Architecture relationship references an unavailable entity.",
                        explanation=(
                            "The relationship cannot be included in the canonical graph because one or more "
                            "endpoints are missing from the current registry state."
                        ),
                        root_project_id=(source.owning_project_or_domain if source else target.owning_project_or_domain if target else None),
                        related_node_ids=[item for item in [source.entity_id if source else None, target.entity_id if target else None] if item is not None],
                        related_edge_ids=[relationship.relationship_id],
                        provenance_references=[relationship.provenance],
                        freshness_state=relationship.freshness_state,
                        trust_state=self._trust_from_freshness(relationship.freshness_state),
                        details={"relationship_identity_key": relationship.identity_key},
                    )
                )
                continue
            edge = self._relationship_edge(relationship, source, target)
            edges.append(edge)
            if source.owning_project_or_domain and target.owning_project_or_domain:
                architecture_support_pairs.add((source.owning_project_or_domain, target.owning_project_or_domain))

        contract_edges: list[DependencyGraphEdge] = []
        for project in projects:
            contract = current_contracts.get(project.project_id)
            project_entity = identity_key_map.get(project.project_id)
            project_node = node_map.get(project_entity.entity_id) if project_entity is not None else None
            if contract is None or project_node is None:
                findings.append(
                    self._finding(
                        finding_type="missing_contract",
                        severity="critical",
                        summary=f"Project contract is unavailable for {project.project_id}.",
                        explanation="The dependency graph cannot fully represent the project without an approved current contract.",
                        root_project_id=project.project_id,
                        related_node_ids=[project_node.node_id] if project_node is not None else [],
                        freshness_state="unavailable",
                        trust_state="unavailable",
                        details={"project_id": project.project_id},
                    )
                )
                continue
            if contract.current_revision is None:
                findings.append(
                    self._finding(
                        finding_type="missing_contract",
                        severity="critical",
                        summary=f"Project contract revision is unavailable for {project.project_id}.",
                        explanation="The dependency graph cannot consume a contract summary without an approved current revision.",
                        root_project_id=project.project_id,
                        related_node_ids=[project_node.node_id],
                        freshness_state="unavailable",
                        trust_state="unavailable",
                        details={"project_id": project.project_id, "contract_id": contract.contract_id},
                    )
                )
                continue
            for declaration in self._contract_declarations(contract.current_revision.content):
                target = self._resolve_reference(declaration["reference"], entities, identity_key_map)
                if target is None:
                    findings.append(
                        self._finding(
                            finding_type="unresolved_dependency",
                            severity="warning",
                            summary="Declared dependency could not be resolved.",
                            explanation=(
                                "The current approved project contract declares a dependency that does not resolve "
                                "to a canonical architecture entity or project."
                            ),
                            root_project_id=project.project_id,
                            root_entity_id=project_node.node_id,
                            related_node_ids=[project_node.node_id],
                            provenance_references=[contract.provenance],
                            freshness_state=contract.freshness_state,
                            trust_state="unknown",
                            details={
                                "field": declaration["field"],
                                "declared_reference": declaration["reference"],
                                "contract_revision_id": contract.current_revision_id,
                            },
                        )
                    )
                    continue
                supported = (
                    project.project_id == target.owning_project_or_domain
                    or (project.project_id, target.owning_project_or_domain or "") in architecture_support_pairs
                )
                edge = self._contract_edge(project_node, target, contract, declaration, supported=supported)
                contract_edges.append(edge)
                if not supported and declaration["field"] in {"dependencies", "shared_packages", "hardware_dependencies", "api_contracts", "data_contracts"}:
                    findings.append(
                        self._finding(
                            finding_type="unsupported_dependency",
                            severity="warning",
                            summary="Declared dependency is not backed by architecture evidence.",
                            explanation=(
                                "The contract declares a dependency, but the current canonical architecture graph does not "
                                "contain supporting architecture relationships between the source and target projects."
                            ),
                            root_project_id=project.project_id,
                            root_entity_id=project_node.node_id,
                            related_node_ids=[project_node.node_id, target.entity_id],
                            related_edge_ids=[edge.edge_id],
                            provenance_references=[contract.provenance, target.provenance],
                            freshness_state=self._merge_freshness(contract.freshness_state, target.freshness_state),
                            trust_state="partial",
                            details={
                                "field": declaration["field"],
                                "declared_reference": declaration["reference"],
                                "resolved_target": target.entity_id,
                            },
                        )
                    )
        edges.extend(contract_edges)

        snapshot_findings = self._findings_for_cycles(nodes, edges)
        snapshot_findings.extend(self._shared_dependency_findings(nodes, edges))
        snapshot_findings.extend(self._orphan_findings(nodes, edges))
        snapshot_findings.extend(findings)
        snapshot_findings = self._dedupe_findings(snapshot_findings)
        snapshot_findings.sort(key=lambda item: (item.finding_type, item.severity, item.finding_id))

        graph_payload = self._fingerprint_payload(nodes, edges, snapshot_findings, current_contracts, entities, relationships)
        graph_fingerprint = _content_fingerprint(graph_payload)
        return DependencyGraphSnapshot(
            graph_id=f"dependency-graph:{graph_fingerprint[:16]}",
            graph_fingerprint=graph_fingerprint,
            source_contract_revision_ids=sorted(
                [contract.current_revision_id for contract in current_contracts.values() if contract.current_revision_id]
            ),
            source_entity_revision_ids=sorted([entity.current_revision_id for entity in entities if entity.current_revision_id]),
            source_relationship_revision_ids=sorted(
                [relationship.current_revision_id for relationship in relationships if relationship.current_revision_id]
            ),
            node_count=len(nodes),
            edge_count=len(edges),
            nodes=sorted(nodes, key=lambda item: item.node_id),
            edges=sorted(edges, key=lambda item: item.edge_id),
            findings=snapshot_findings,
            freshness_state=self._combine_freshness(
                [*(node.freshness_state for node in nodes), *(edge.freshness_state for edge in edges)]
            ),
            trust_state=self._combine_trust(
                [*(node.trust_state for node in nodes), *(edge.trust_state for edge in edges), *(finding.trust_state for finding in snapshot_findings)]
            ),
        )

    def get_node(self, node_id: str) -> DependencyGraphNode | None:
        return self._snapshot_index().nodes.get(node_id)

    def get_edge(self, edge_id: str) -> DependencyGraphEdge | None:
        return self._snapshot_index().edges.get(edge_id)

    def dependencies_of_entity(
        self,
        entity_id: str,
        *,
        transitive: bool = False,
    ) -> list[DependencyGraphDependencyRecord]:
        snapshot = self.build_graph()
        return self._dependencies_from_snapshot(snapshot, entity_id, transitive=transitive)

    def dependents_of_entity(
        self,
        entity_id: str,
        *,
        transitive: bool = False,
    ) -> list[DependencyGraphDependencyRecord]:
        snapshot = self.build_graph()
        return self._dependents_from_snapshot(snapshot, entity_id, transitive=transitive)

    def dependencies_of_project(
        self,
        project_id: str,
        *,
        transitive: bool = False,
    ) -> list[DependencyGraphProjectDependencyRecord]:
        snapshot = self.build_graph()
        return self._project_dependencies_from_snapshot(snapshot, project_id, transitive=transitive)

    def dependents_of_project(
        self,
        project_id: str,
        *,
        transitive: bool = False,
    ) -> list[DependencyGraphProjectDependencyRecord]:
        snapshot = self.build_graph()
        return self._project_dependents_from_snapshot(snapshot, project_id, transitive=transitive)

    def project_dependencies(
        self,
        project_id: str,
        *,
        transitive: bool = False,
    ) -> list[DependencyGraphProjectDependencyRecord]:
        return self.dependencies_of_project(project_id, transitive=transitive)

    def project_dependents(
        self,
        project_id: str,
        *,
        transitive: bool = False,
    ) -> list[DependencyGraphProjectDependencyRecord]:
        return self.dependents_of_project(project_id, transitive=transitive)

    def shared_dependencies(self) -> list[DependencyGraphSharedDependencyRecord]:
        snapshot = self.build_graph()
        return self._shared_dependencies_from_snapshot(snapshot)

    def cycles(self) -> list[DependencyGraphCycleRecord]:
        snapshot = self.build_graph()
        return self._cycles_from_snapshot(snapshot)

    def orphans(self) -> list[DependencyGraphOrphanRecord]:
        snapshot = self.build_graph()
        return self._orphans_from_snapshot(snapshot)

    def unresolved_dependencies(self) -> list[DependencyGraphFinding]:
        return [item for item in self.build_graph().findings if item.finding_type in {"unresolved_dependency", "missing_contract", "unsupported_dependency", "conflict"}]

    def graph_fingerprint(self) -> str:
        return self.build_graph().graph_fingerprint

    def project_dependency_projection(self, project_id: str, *, transitive: bool = False) -> list[DependencyGraphProjectDependencyRecord]:
        return self.dependencies_of_project(project_id, transitive=transitive)

    def project_dependents_projection(self, project_id: str, *, transitive: bool = False) -> list[DependencyGraphProjectDependencyRecord]:
        return self.dependents_of_project(project_id, transitive=transitive)

    def _snapshot_index(self) -> _DependencyGraphIndex:
        snapshot = self.build_graph()
        return _DependencyGraphIndex(
            nodes={node.node_id: node for node in snapshot.nodes},
            edges={edge.edge_id: edge for edge in snapshot.edges},
        )

    def _current_contracts(self, projects: list[ProjectConfig]) -> dict[str, ProjectContractRecord]:
        contracts: dict[str, ProjectContractRecord] = {}
        for project in projects:
            contract = self.project_contract_service.current_approved_contract(project.project_id)
            if contract is not None:
                contracts[project.project_id] = contract
        return dict(sorted(contracts.items(), key=lambda item: item[0]))

    def _current_entities(self) -> list[ArchitectureEntityRecord]:
        entities = [
            entity
            for entity in self.architecture_registry_service.list_entities()
            if entity.current_revision_id is not None and entity.status == "approved"
        ]
        return sorted(entities, key=lambda item: item.entity_id)

    def _current_relationships(self) -> list[ArchitectureRelationshipRecord]:
        relationships = [
            relationship
            for relationship in self.architecture_registry_service.list_relationships()
            if relationship.current_revision_id is not None and relationship.status == "approved"
        ]
        return sorted(relationships, key=lambda item: item.relationship_id)

    def _node_from_entity(
        self,
        entity: ArchitectureEntityRecord,
        contract: ProjectContractRecord | None,
    ) -> DependencyGraphNode:
        freshness = entity.freshness_state
        trust_state = self._trust_from_freshness(freshness)
        if contract is None and entity.entity_id == f"architecture-entity:project:{entity.identity_key}":
            trust_state = "unavailable"
        if contract is not None:
            freshness = self._merge_freshness(freshness, contract.freshness_state)
            trust_state = self._combine_trust([trust_state, self._trust_from_freshness(contract.freshness_state)])
        return DependencyGraphNode(
            node_id=entity.entity_id,
            architecture_entity_id=entity.entity_id,
            entity_kind=entity.kind,
            owning_project_or_domain=entity.owning_project_or_domain,
            current_entity_revision_id=entity.current_revision_id,
            status=entity.status,
            provenance=entity.provenance,
            freshness_state=freshness,
            trust_state=trust_state,
            current_contract_revision_id=contract.current_revision_id if contract is not None else None,
        )

    def _relationship_edge(
        self,
        relationship: ArchitectureRelationshipRecord,
        source: ArchitectureEntityRecord,
        target: ArchitectureEntityRecord,
    ) -> DependencyGraphEdge:
        provenance = relationship.provenance
        freshness = self._merge_freshness(source.freshness_state, target.freshness_state, relationship.freshness_state)
        trust_state = self._combine_trust(
            [
                self._trust_from_freshness(source.freshness_state),
                self._trust_from_freshness(target.freshness_state),
                self._trust_from_freshness(relationship.freshness_state),
            ]
        )
        return DependencyGraphEdge(
            edge_id=relationship.relationship_id,
            source_node_id=source.entity_id,
            target_node_id=target.entity_id,
            source_entity_id=source.entity_id,
            target_entity_id=target.entity_id,
            relationship_type=relationship.relationship_type,
            canonical_relationship_reference=relationship.identity_key,
            provenance=provenance,
            freshness_state=freshness,
            trust_state=trust_state,
            source_revision_id=source.current_revision_id,
            target_revision_id=target.current_revision_id,
        )

    def _contract_edge(
        self,
        project_node: DependencyGraphNode,
        target: ArchitectureEntityRecord,
        contract: ProjectContractRecord,
        declaration: dict[str, Any],
        *,
        supported: bool,
    ) -> DependencyGraphEdge:
        relationship_type = declaration["relationship_type"]
        declared_reference = declaration["reference"]
        raw_payload = {
            "project_id": project_node.node_id,
            "contract_id": contract.contract_id,
            "contract_revision_id": contract.current_revision_id,
            "field": declaration["field"],
            "reference": declared_reference,
            "target_entity_id": target.entity_id,
        }
        edge_id = _deterministic_id("dependency-edge", raw_payload)
        freshness = self._merge_freshness(contract.freshness_state, target.freshness_state)
        trust_state = self._trust_from_freshness(freshness) if supported else "partial"
        return DependencyGraphEdge(
            edge_id=edge_id,
            source_node_id=project_node.node_id,
            target_node_id=target.entity_id,
            source_entity_id=project_node.node_id,
            target_entity_id=target.entity_id,
            relationship_type=relationship_type,
            canonical_relationship_reference=f"{contract.contract_id}:{contract.current_revision_id}:{declaration['field']}:{declared_reference}",
            provenance=contract.provenance,
            freshness_state=freshness,
            trust_state=trust_state,
            version_constraint=declaration.get("version_constraint"),
            contract_constraint={
                "field": declaration["field"],
                "reference": declared_reference,
                "contract_id": contract.contract_id,
                "contract_revision_id": contract.current_revision_id,
            },
            declared_reference=declared_reference,
        )

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

    def _resolve_reference(
        self,
        reference: str,
        entities: list[ArchitectureEntityRecord],
        identity_key_map: dict[str, ArchitectureEntityRecord],
    ) -> ArchitectureEntityRecord | None:
        for entity in entities:
            if entity.entity_id == reference:
                return entity
        return identity_key_map.get(reference)

    def _dependencies_from_snapshot(
        self,
        snapshot: DependencyGraphSnapshot,
        root_entity_id: str,
        *,
        transitive: bool,
    ) -> list[DependencyGraphDependencyRecord]:
        node_ids = {node.node_id for node in snapshot.nodes}
        if root_entity_id not in node_ids:
            raise KeyError(f"Unknown entity: {root_entity_id}")
        outgoing = self._outgoing_edges(snapshot.edges)
        root = self._node_by_id(snapshot.nodes, root_entity_id)
        if root is None:
            raise KeyError(f"Unknown entity: {root_entity_id}")
        if not transitive:
            records: list[DependencyGraphDependencyRecord] = []
            for edge in outgoing[root_entity_id]:
                target = self._node_by_id(snapshot.nodes, edge.target_node_id)
                if target is None:
                    continue
                records.append(self._dependency_record(root, target, [edge]))
            return sorted(records, key=lambda item: (item.depth, item.node_id, item.dependency_id))

        return self._traverse_dependencies(snapshot, root_entity_id, outgoing=outgoing)

    def _dependents_from_snapshot(
        self,
        snapshot: DependencyGraphSnapshot,
        root_entity_id: str,
        *,
        transitive: bool,
    ) -> list[DependencyGraphDependencyRecord]:
        node_ids = {node.node_id for node in snapshot.nodes}
        if root_entity_id not in node_ids:
            raise KeyError(f"Unknown entity: {root_entity_id}")
        incoming = self._incoming_edges(snapshot.edges)
        root = self._node_by_id(snapshot.nodes, root_entity_id)
        if root is None:
            raise KeyError(f"Unknown entity: {root_entity_id}")
        if not transitive:
            records: list[DependencyGraphDependencyRecord] = []
            for edge in incoming[root_entity_id]:
                source = self._node_by_id(snapshot.nodes, edge.source_node_id)
                if source is None:
                    continue
                records.append(self._dependency_record(root, source, [edge]))
            return sorted(records, key=lambda item: (item.depth, item.node_id, item.dependency_id))
        return self._traverse_dependents(snapshot, root_entity_id, incoming=incoming)

    def _project_dependencies_from_snapshot(
        self,
        snapshot: DependencyGraphSnapshot,
        project_id: str,
        *,
        transitive: bool,
    ) -> list[DependencyGraphProjectDependencyRecord]:
        root_id = f"architecture-entity:project:{project_id}"
        root = self._node_by_id(snapshot.nodes, root_id)
        if root is None:
            raise KeyError(f"Unknown project: {project_id}")
        dependencies = self._dependencies_from_snapshot(snapshot, root_id, transitive=transitive)
        return self._project_dependency_projection(root, dependencies, project_id)

    def _project_dependents_from_snapshot(
        self,
        snapshot: DependencyGraphSnapshot,
        project_id: str,
        *,
        transitive: bool,
    ) -> list[DependencyGraphProjectDependencyRecord]:
        root_id = f"architecture-entity:project:{project_id}"
        root = self._node_by_id(snapshot.nodes, root_id)
        if root is None:
            raise KeyError(f"Unknown project: {project_id}")
        dependents = self._dependents_from_snapshot(snapshot, root_id, transitive=transitive)
        return self._project_dependency_projection(root, dependents, project_id, reverse=True)

    def _project_dependency_projection(
        self,
        root: DependencyGraphNode,
        dependency_records: list[DependencyGraphDependencyRecord],
        source_project_id: str,
        *,
        reverse: bool = False,
    ) -> list[DependencyGraphProjectDependencyRecord]:
        grouped: dict[str, list[DependencyGraphDependencyRecord]] = defaultdict(list)
        for record in dependency_records:
            target_project_id = record.owning_project_or_domain or record.node_id
            if target_project_id == source_project_id:
                continue
            grouped[target_project_id].append(record)

        projected: list[DependencyGraphProjectDependencyRecord] = []
        for target_project_id, records in sorted(grouped.items(), key=lambda item: item[0]):
            representative = sorted(records, key=lambda item: (item.depth, item.node_id, item.dependency_id))[0]
            if reverse:
                output_source_project_id = target_project_id
                output_target_project_id = source_project_id
                source_project_node_id = f"architecture-entity:project:{target_project_id}"
                target_project_node_id = root.node_id
            else:
                output_source_project_id = source_project_id
                output_target_project_id = target_project_id
                source_project_node_id = root.node_id
                target_project_node_id = f"architecture-entity:project:{target_project_id}"
            projected.append(
                DependencyGraphProjectDependencyRecord(
                    project_dependency_id=_deterministic_id(
                        "project-dependency",
                        {
                            "source_project_id": output_source_project_id,
                            "target_project_id": output_target_project_id,
                            "representative_dependency_id": representative.dependency_id,
                        },
                    ),
                    source_project_id=output_source_project_id,
                    target_project_id=output_target_project_id,
                    source_project_node_id=source_project_node_id,
                    target_project_node_id=target_project_node_id,
                    representative_dependency_id=representative.dependency_id,
                    representative_path_node_ids=representative.path_node_ids,
                    representative_path_edge_ids=representative.path_edge_ids,
                    supporting_node_ids=sorted({record.node_id for record in records}),
                    supporting_edge_ids=sorted({edge_id for record in records for edge_id in record.path_edge_ids}),
                    relationship_types=_dedupe_preserve_order(
                        [relationship_type for record in records for relationship_type in record.relationship_types]
                    ),
                    provenance_references=_dedupe_provenance(
                        [provenance for record in records for provenance in record.provenance_references]
                    ),
                    freshness_state=self._combine_freshness([record.freshness_state for record in records]),
                    trust_state=self._combine_trust([record.trust_state for record in records]),
                    declared_references=_dedupe_preserve_order(
                        [record.declared_reference for record in records if record.declared_reference is not None]
                    ),
                    contract_constraints=[constraint for record in records for constraint in ([record.contract_constraint] if record.contract_constraint else [])],
                    version_constraints=_dedupe_preserve_order(
                        [constraint for record in records for constraint in ([record.version_constraint] if record.version_constraint else [])]
                    ),
                )
            )
        return projected

    def _traverse_dependencies(
        self,
        snapshot: DependencyGraphSnapshot,
        root_entity_id: str,
        *,
        outgoing: dict[str, list[DependencyGraphEdge]],
    ) -> list[DependencyGraphDependencyRecord]:
        root = self._node_by_id(snapshot.nodes, root_entity_id)
        if root is None:
            raise KeyError(f"Unknown entity: {root_entity_id}")
        queue: deque[tuple[str, list[str], list[str], list[ProgrammeProvenanceRecord], list[ArchitectureRelationshipType], EvidenceFreshnessState, DependencyGraphTrustState, str | None, dict[str, Any] | None, str | None]] = deque()
        queue.append((root_entity_id, [root_entity_id], [], [root.provenance], [], root.freshness_state, root.trust_state, None, None, None))
        best: dict[str, DependencyGraphDependencyRecord] = {}
        while queue:
            current_node_id, path_nodes, path_edges, provenance_refs, relationship_types, freshness, trust_state, declared_reference, contract_constraint, version_constraint = queue.popleft()
            for edge in outgoing.get(current_node_id, []):
                next_node = self._node_by_id(snapshot.nodes, edge.target_node_id)
                if next_node is None:
                    continue
                next_path_nodes = path_nodes + [next_node.node_id]
                next_path_edges = path_edges + [edge.edge_id]
                next_provenance_refs = _dedupe_provenance([*provenance_refs, edge.provenance])
                next_relationship_types = _dedupe_preserve_order([*relationship_types, edge.relationship_type])
                next_freshness = self._merge_freshness(freshness, edge.freshness_state)
                next_trust_state = self._combine_trust([trust_state, edge.trust_state, next_node.trust_state])
                record = self._dependency_record(
                    root,
                    next_node,
                    [edge],
                    depth=len(next_path_edges),
                    path_node_ids=next_path_nodes,
                    path_edge_ids=next_path_edges,
                    provenance_references=next_provenance_refs,
                    relationship_types=next_relationship_types,
                    freshness_state=next_freshness,
                    trust_state=next_trust_state,
                    declared_reference=edge.declared_reference,
                    contract_constraint=edge.contract_constraint,
                    version_constraint=edge.version_constraint,
                )
                existing = best.get(next_node.node_id)
                if existing is None or self._dependency_sort_key(record) < self._dependency_sort_key(existing):
                    best[next_node.node_id] = record
                if next_node.node_id not in path_nodes:
                    queue.append(
                        (
                            next_node.node_id,
                            next_path_nodes,
                            next_path_edges,
                            next_provenance_refs,
                            next_relationship_types,
                            next_freshness,
                            next_trust_state,
                            edge.declared_reference,
                            edge.contract_constraint,
                            edge.version_constraint,
                        )
                    )
        records = [record for node_id, record in best.items() if node_id != root_entity_id]
        return sorted(records, key=self._dependency_sort_key)

    def _traverse_dependents(
        self,
        snapshot: DependencyGraphSnapshot,
        root_entity_id: str,
        *,
        incoming: dict[str, list[DependencyGraphEdge]],
    ) -> list[DependencyGraphDependencyRecord]:
        root = self._node_by_id(snapshot.nodes, root_entity_id)
        if root is None:
            raise KeyError(f"Unknown entity: {root_entity_id}")
        queue: deque[tuple[str, list[str], list[str], list[ProgrammeProvenanceRecord], list[ArchitectureRelationshipType], EvidenceFreshnessState, DependencyGraphTrustState, str | None, dict[str, Any] | None, str | None]] = deque()
        queue.append((root_entity_id, [root_entity_id], [], [root.provenance], [], root.freshness_state, root.trust_state, None, None, None))
        best: dict[str, DependencyGraphDependencyRecord] = {}
        while queue:
            current_node_id, path_nodes, path_edges, provenance_refs, relationship_types, freshness, trust_state, declared_reference, contract_constraint, version_constraint = queue.popleft()
            for edge in incoming.get(current_node_id, []):
                next_node = self._node_by_id(snapshot.nodes, edge.source_node_id)
                if next_node is None:
                    continue
                next_path_nodes = path_nodes + [next_node.node_id]
                next_path_edges = path_edges + [edge.edge_id]
                next_provenance_refs = _dedupe_provenance([edge.provenance, *provenance_refs])
                next_relationship_types = _dedupe_preserve_order([edge.relationship_type, *relationship_types])
                next_freshness = self._merge_freshness(freshness, edge.freshness_state)
                next_trust_state = self._combine_trust([trust_state, edge.trust_state, next_node.trust_state])
                record = self._dependency_record(
                    root,
                    next_node,
                    [edge],
                    depth=len(next_path_edges),
                    path_node_ids=list(reversed(next_path_nodes)),
                    path_edge_ids=list(reversed(next_path_edges)),
                    provenance_references=next_provenance_refs,
                    relationship_types=next_relationship_types,
                    freshness_state=next_freshness,
                    trust_state=next_trust_state,
                    declared_reference=edge.declared_reference,
                    contract_constraint=edge.contract_constraint,
                    version_constraint=edge.version_constraint,
                )
                existing = best.get(next_node.node_id)
                if existing is None or self._dependency_sort_key(record) < self._dependency_sort_key(existing):
                    best[next_node.node_id] = record
                if next_node.node_id not in path_nodes:
                    queue.append(
                        (
                            next_node.node_id,
                            next_path_nodes,
                            next_path_edges,
                            next_provenance_refs,
                            next_relationship_types,
                            next_freshness,
                            next_trust_state,
                            edge.declared_reference,
                            edge.contract_constraint,
                            edge.version_constraint,
                        )
                    )
        records = [record for node_id, record in best.items() if node_id != root_entity_id]
        return sorted(records, key=self._dependency_sort_key)

    def _dependency_record(
        self,
        root: DependencyGraphNode,
        node: DependencyGraphNode,
        edges: list[DependencyGraphEdge],
        *,
        depth: int | None = None,
        path_node_ids: list[str] | None = None,
        path_edge_ids: list[str] | None = None,
        provenance_references: list[ProgrammeProvenanceRecord] | None = None,
        relationship_types: list[ArchitectureRelationshipType] | None = None,
        freshness_state: EvidenceFreshnessState | None = None,
        trust_state: DependencyGraphTrustState | None = None,
        declared_reference: str | None = None,
        contract_constraint: dict[str, Any] | None = None,
        version_constraint: str | None = None,
    ) -> DependencyGraphDependencyRecord:
        if depth is None:
            depth = len(edges)
        if path_node_ids is None:
            path_node_ids = [root.node_id, node.node_id]
        if path_edge_ids is None:
            path_edge_ids = [edge.edge_id for edge in edges]
        if provenance_references is None:
            provenance_references = [edge.provenance for edge in edges]
        if relationship_types is None:
            relationship_types = [edge.relationship_type for edge in edges]
        if freshness_state is None:
            freshness_state = self._combine_freshness([root.freshness_state, node.freshness_state, *(edge.freshness_state for edge in edges)])
        if trust_state is None:
            trust_state = self._combine_trust([root.trust_state, node.trust_state, *(edge.trust_state for edge in edges)])
        return DependencyGraphDependencyRecord(
            dependency_id=_deterministic_id(
                "dependency-record",
                {
                    "root_node_id": root.node_id,
                    "node_id": node.node_id,
                    "path_edge_ids": path_edge_ids,
                    "path_node_ids": path_node_ids,
                    "declared_reference": declared_reference,
                },
            ),
            root_node_id=root.node_id,
            node_id=node.node_id,
            architecture_entity_id=node.architecture_entity_id,
            entity_kind=node.entity_kind,
            owning_project_or_domain=node.owning_project_or_domain,
            depth=depth,
            path_node_ids=path_node_ids,
            path_edge_ids=path_edge_ids,
            relationship_types=_dedupe_preserve_order(relationship_types),
            provenance_references=_dedupe_provenance(provenance_references),
            freshness_state=freshness_state,
            trust_state=trust_state,
            declared_reference=declared_reference,
            contract_constraint=contract_constraint,
            version_constraint=version_constraint,
        )

    def _cycles_from_snapshot(self, snapshot: DependencyGraphSnapshot) -> list[DependencyGraphCycleRecord]:
        outgoing = self._outgoing_edges(snapshot.edges)
        index = 0
        indices: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        components: list[list[str]] = []

        def strongconnect(node_id: str) -> None:
            nonlocal index
            indices[node_id] = index
            lowlinks[node_id] = index
            index += 1
            stack.append(node_id)
            on_stack.add(node_id)
            for edge in outgoing.get(node_id, []):
                target = edge.target_node_id
                if target not in indices:
                    strongconnect(target)
                    lowlinks[node_id] = min(lowlinks[node_id], lowlinks[target])
                elif target in on_stack:
                    lowlinks[node_id] = min(lowlinks[node_id], indices[target])
            if lowlinks[node_id] == indices[node_id]:
                component: list[str] = []
                while True:
                    item = stack.pop()
                    on_stack.remove(item)
                    component.append(item)
                    if item == node_id:
                        break
                components.append(sorted(component))

        for node in sorted(snapshot.nodes, key=lambda item: item.node_id):
            if node.node_id not in indices:
                strongconnect(node.node_id)

        cycles: list[DependencyGraphCycleRecord] = []
        for component in components:
            if len(component) == 1:
                node_id = component[0]
                self_edges = [edge for edge in outgoing.get(node_id, []) if edge.target_node_id == node_id]
                if not self_edges:
                    continue
                edge_ids = sorted(edge.edge_id for edge in self_edges)
            else:
                component_set = set(component)
                edge_ids = sorted(
                    edge.edge_id
                    for source in component
                    for edge in outgoing.get(source, [])
                    if edge.target_node_id in component_set
                )
            edges: list[DependencyGraphEdge] = []
            for edge_id in edge_ids:
                edge = self._edge_by_id(snapshot.edges, edge_id)
                if edge is None:
                    continue
                edges.append(edge)
            nodes: list[DependencyGraphNode] = []
            for node_id in component:
                component_node: DependencyGraphNode | None = self._node_by_id(snapshot.nodes, node_id)
                if component_node is None:
                    continue
                nodes.append(component_node)
            project_ids: list[str] = []
            for node in nodes:
                if node.owning_project_or_domain is None:
                    continue
                project_ids.append(node.owning_project_or_domain)
            relationship_types: list[ArchitectureRelationshipType] = []
            for edge in edges:
                relationship_types.append(edge.relationship_type)
            cycles.append(
                DependencyGraphCycleRecord(
                    cycle_id=_deterministic_id("dependency-cycle", {"nodes": component, "edges": edge_ids}),
                    node_ids=component,
                    edge_ids=edge_ids,
                    project_ids=sorted(_dedupe_preserve_order(project_ids)),
                    relationship_types=_dedupe_preserve_order(relationship_types),
                    provenance_references=_dedupe_provenance([edge.provenance for edge in edges]),
                    freshness_state=self._combine_freshness([edge.freshness_state for edge in edges]),
                    trust_state=self._combine_trust([edge.trust_state for edge in edges]),
                    details={"component_size": len(component)},
                )
            )
        cycles.sort(key=lambda item: item.cycle_id)
        return cycles

    def _shared_dependencies_from_snapshot(self, snapshot: DependencyGraphSnapshot) -> list[DependencyGraphSharedDependencyRecord]:
        incoming = self._incoming_edges(snapshot.edges)
        shared: list[DependencyGraphSharedDependencyRecord] = []
        for node in sorted(snapshot.nodes, key=lambda item: item.node_id):
            dependents = incoming.get(node.node_id, [])
            dependent_node_ids = sorted({edge.source_node_id for edge in dependents if edge.source_node_id != node.node_id})
            dependent_project_ids: list[str] = []
            for edge in dependents:
                source_node = self._node_by_id(snapshot.nodes, edge.source_node_id)
                if source_node is None or source_node.owning_project_or_domain is None:
                    continue
                dependent_project_ids.append(source_node.owning_project_or_domain)
            if len(dependent_node_ids) < 2:
                continue
            edges = [edge for edge in dependents if edge.source_node_id in dependent_node_ids]
            shared.append(
                DependencyGraphSharedDependencyRecord(
                    shared_dependency_id=_deterministic_id(
                        "shared-dependency",
                        {"node_id": node.node_id, "dependent_node_ids": dependent_node_ids},
                    ),
                    node_id=node.node_id,
                    architecture_entity_id=node.architecture_entity_id,
                    entity_kind=node.entity_kind,
                    owning_project_or_domain=node.owning_project_or_domain,
                    dependent_node_ids=dependent_node_ids,
                    dependent_project_ids=sorted(_dedupe_preserve_order(dependent_project_ids)),
                    edge_ids=sorted({edge.edge_id for edge in edges}),
                    relationship_types=_dedupe_preserve_order([edge.relationship_type for edge in edges]),
                    provenance_references=_dedupe_provenance([edge.provenance for edge in edges]),
                    freshness_state=self._combine_freshness([edge.freshness_state for edge in edges]),
                    trust_state=self._combine_trust([edge.trust_state for edge in edges]),
                    details={"dependent_count": len(dependent_node_ids)},
                )
            )
        shared.sort(key=lambda item: item.shared_dependency_id)
        return shared

    def _orphan_findings(self, nodes: list[DependencyGraphNode], edges: list[DependencyGraphEdge]) -> list[DependencyGraphFinding]:
        incident_counts: dict[str, int] = defaultdict(int)
        for edge in edges:
            incident_counts[edge.source_node_id] += 1
            incident_counts[edge.target_node_id] += 1
        findings: list[DependencyGraphFinding] = []
        for node in sorted(nodes, key=lambda item: item.node_id):
            if node.entity_kind == "project":
                continue
            if incident_counts.get(node.node_id, 0) > 0:
                continue
            findings.append(
                self._finding(
                    finding_type="orphan",
                    severity="info",
                    summary="Architecture entity is currently orphaned.",
                    explanation="The entity has no qualifying approved incoming or outgoing dependency relationships in the canonical graph.",
                    root_project_id=node.owning_project_or_domain,
                    root_entity_id=node.node_id,
                    related_node_ids=[node.node_id],
                    provenance_references=[node.provenance],
                    freshness_state=node.freshness_state,
                    trust_state=node.trust_state,
                    details={"entity_kind": node.entity_kind, "reason": "no_incident_edges"},
                )
            )
        return findings

    def _shared_dependency_findings(self, nodes: list[DependencyGraphNode], edges: list[DependencyGraphEdge]) -> list[DependencyGraphFinding]:
        findings: list[DependencyGraphFinding] = []
        incoming = self._incoming_edges(edges)
        for node in sorted(nodes, key=lambda item: item.node_id):
            dependents = incoming.get(node.node_id, [])
            dependent_project_values: list[str] = []
            for edge in dependents:
                source_node = self._node_by_id(nodes, edge.source_node_id)
                if source_node is None or source_node.owning_project_or_domain is None:
                    continue
                dependent_project_values.append(source_node.owning_project_or_domain)
            dependent_projects = sorted({project_id for project_id in dependent_project_values})
            if len(dependent_projects) < 2:
                continue
            findings.append(
                self._finding(
                    finding_type="shared_dependency",
                    severity="info",
                    summary="Architecture entity is shared by multiple projects.",
                    explanation="The entity is depended on by multiple canonical projects or project-owned entities.",
                    root_project_id=node.owning_project_or_domain,
                    root_entity_id=node.node_id,
                    related_node_ids=sorted({edge.source_node_id for edge in dependents} | {node.node_id}),
                    related_edge_ids=sorted({edge.edge_id for edge in dependents}),
                    provenance_references=[node.provenance, *[edge.provenance for edge in dependents]],
                    freshness_state=self._combine_freshness([node.freshness_state, *[edge.freshness_state for edge in dependents]]),
                    trust_state=self._combine_trust([node.trust_state, *[edge.trust_state for edge in dependents]]),
                    details={"dependent_project_ids": dependent_projects},
                )
            )
        return findings

    def _findings_for_cycles(self, nodes: list[DependencyGraphNode], edges: list[DependencyGraphEdge]) -> list[DependencyGraphFinding]:
        cycles = self._cycles_from_snapshot(
            DependencyGraphSnapshot(
                graph_id="temporary",
                graph_fingerprint="temporary",
                nodes=nodes,
                edges=edges,
            )
        )
        findings: list[DependencyGraphFinding] = []
        for cycle in cycles:
            findings.append(
                self._finding(
                    finding_type="cycle",
                    severity="warning",
                    summary="Dependency cycle detected.",
                    explanation="The canonical graph contains a deterministic cycle across approved dependency records.",
                    related_node_ids=cycle.node_ids,
                    related_edge_ids=cycle.edge_ids,
                    provenance_references=cycle.provenance_references,
                    freshness_state=cycle.freshness_state,
                    trust_state=cycle.trust_state,
                    details=cycle.model_dump(mode="json"),
                )
            )
        return findings

    def _orphans_from_snapshot(self, snapshot: DependencyGraphSnapshot) -> list[DependencyGraphOrphanRecord]:
        incoming = self._incoming_edges(snapshot.edges)
        outgoing = self._outgoing_edges(snapshot.edges)
        orphans: list[DependencyGraphOrphanRecord] = []
        for node in sorted(snapshot.nodes, key=lambda item: item.node_id):
            if node.entity_kind == "project":
                continue
            if incoming.get(node.node_id) or outgoing.get(node.node_id):
                continue
            orphans.append(
                DependencyGraphOrphanRecord(
                    orphan_id=_deterministic_id("orphan", {"node_id": node.node_id}),
                    node_id=node.node_id,
                    architecture_entity_id=node.architecture_entity_id,
                    entity_kind=node.entity_kind,
                    owning_project_or_domain=node.owning_project_or_domain,
                    reason="no_incident_edges",
                    provenance=node.provenance,
                    freshness_state=node.freshness_state,
                    trust_state=node.trust_state,
                )
            )
        return orphans

    def _finding(
        self,
        *,
        finding_type: DependencyGraphFindingType,
        severity: Literal["info", "warning", "critical"],
        summary: str,
        explanation: str,
        root_project_id: str | None = None,
        root_entity_id: str | None = None,
        related_node_ids: list[str] | None = None,
        related_edge_ids: list[str] | None = None,
        provenance_references: list[ProgrammeProvenanceRecord] | None = None,
        freshness_state: EvidenceFreshnessState = "unknown",
        trust_state: DependencyGraphTrustState = "unknown",
        details: dict[str, Any] | None = None,
    ) -> DependencyGraphFinding:
        payload = {
            "finding_type": finding_type,
            "root_project_id": root_project_id,
            "root_entity_id": root_entity_id,
            "related_node_ids": related_node_ids or [],
            "related_edge_ids": related_edge_ids or [],
            "summary": summary,
            "explanation": explanation,
            "details": details or {},
        }
        return DependencyGraphFinding(
            finding_id=_deterministic_id("dependency-finding", payload),
            finding_type=finding_type,
            severity=severity,
            summary=summary,
            explanation=explanation,
            root_project_id=root_project_id,
            root_entity_id=root_entity_id,
            related_node_ids=_dedupe_preserve_order(related_node_ids or []),
            related_edge_ids=_dedupe_preserve_order(related_edge_ids or []),
            provenance_references=_dedupe_provenance(provenance_references or []),
            freshness_state=freshness_state,
            trust_state=trust_state,
            details=details or {},
        )

    def _fingerprint_payload(
        self,
        nodes: list[DependencyGraphNode],
        edges: list[DependencyGraphEdge],
        findings: list[DependencyGraphFinding],
        current_contracts: dict[str, ProjectContractRecord],
        entities: list[ArchitectureEntityRecord],
        relationships: list[ArchitectureRelationshipRecord],
    ) -> dict[str, Any]:
        return {
            "nodes": [self._fingerprint_node(node) for node in sorted(nodes, key=lambda item: item.node_id)],
            "edges": [self._fingerprint_edge(edge) for edge in sorted(edges, key=lambda item: item.edge_id)],
            "findings": [self._fingerprint_finding(finding) for finding in findings],
            "source_contract_fingerprints": sorted(
                [self._semantic_contract_fingerprint(contract) for contract in current_contracts.values() if contract.current_revision is not None]
            ),
            "source_entity_fingerprints": sorted(
                [self._semantic_entity_fingerprint(entity) for entity in entities if entity.current_revision is not None]
            ),
            "source_relationship_fingerprints": sorted(
                [self._semantic_relationship_fingerprint(relationship) for relationship in relationships if relationship.current_revision is not None]
            ),
        }

    def _fingerprint_node(self, node: DependencyGraphNode) -> dict[str, Any]:
        return {
            "node_id": node.node_id,
            "architecture_entity_id": node.architecture_entity_id,
            "entity_kind": node.entity_kind,
            "owning_project_or_domain": node.owning_project_or_domain,
            "status": node.status,
            "freshness_state": node.freshness_state,
            "trust_state": node.trust_state,
        }

    def _fingerprint_edge(self, edge: DependencyGraphEdge) -> dict[str, Any]:
        return {
            "edge_id": edge.edge_id,
            "source_node_id": edge.source_node_id,
            "target_node_id": edge.target_node_id,
            "source_entity_id": edge.source_entity_id,
            "target_entity_id": edge.target_entity_id,
            "relationship_type": edge.relationship_type,
            "canonical_relationship_reference": edge.canonical_relationship_reference,
            "freshness_state": edge.freshness_state,
            "trust_state": edge.trust_state,
            "version_constraint": edge.version_constraint,
            "contract_constraint": edge.contract_constraint,
            "declared_reference": edge.declared_reference,
        }

    def _fingerprint_finding(self, finding: DependencyGraphFinding) -> dict[str, Any]:
        return {
            "finding_id": finding.finding_id,
            "finding_type": finding.finding_type,
            "severity": finding.severity,
            "summary": finding.summary,
            "explanation": finding.explanation,
            "root_project_id": finding.root_project_id,
            "root_entity_id": finding.root_entity_id,
            "related_node_ids": finding.related_node_ids,
            "related_edge_ids": finding.related_edge_ids,
            "freshness_state": finding.freshness_state,
            "trust_state": finding.trust_state,
            "details": finding.details,
        }

    def _semantic_contract_fingerprint(self, contract: ProjectContractRecord) -> str:
        if contract.current_revision is None:
            return ""
        return _content_fingerprint(contract.current_revision.content.model_dump())

    def _semantic_entity_fingerprint(self, entity: ArchitectureEntityRecord) -> str:
        if entity.current_revision is None:
            return ""
        return _content_fingerprint(entity.current_revision.content.model_dump(exclude={"provenance"}))

    def _semantic_relationship_fingerprint(self, relationship: ArchitectureRelationshipRecord) -> str:
        if relationship.current_revision is None:
            return ""
        return _content_fingerprint(relationship.current_revision.content.model_dump(exclude={"provenance"}))

    def _dependency_sort_key(self, record: DependencyGraphDependencyRecord) -> tuple[int, str, str]:
        return (record.depth, record.node_id, record.dependency_id)

    def _node_by_id(self, nodes: list[DependencyGraphNode], node_id: str) -> DependencyGraphNode | None:
        for node in nodes:
            if node.node_id == node_id:
                return node
        return None

    def _edge_by_id(self, edges: list[DependencyGraphEdge], edge_id: str) -> DependencyGraphEdge | None:
        for edge in edges:
            if edge.edge_id == edge_id:
                return edge
        return None

    def _outgoing_edges(self, edges: list[DependencyGraphEdge]) -> dict[str, list[DependencyGraphEdge]]:
        mapping: dict[str, list[DependencyGraphEdge]] = defaultdict(list)
        for edge in sorted(edges, key=lambda item: (item.source_node_id, item.target_node_id, item.edge_id)):
            mapping[edge.source_node_id].append(edge)
        return mapping

    def _incoming_edges(self, edges: list[DependencyGraphEdge]) -> dict[str, list[DependencyGraphEdge]]:
        mapping: dict[str, list[DependencyGraphEdge]] = defaultdict(list)
        for edge in sorted(edges, key=lambda item: (item.target_node_id, item.source_node_id, item.edge_id)):
            mapping[edge.target_node_id].append(edge)
        return mapping

    def _trust_from_freshness(self, freshness_state: EvidenceFreshnessState) -> DependencyGraphTrustState:
        if freshness_state == "fresh":
            return "trusted"
        if freshness_state == "stale":
            return "stale"
        if freshness_state == "unavailable":
            return "unavailable"
        return "unknown"

    def _merge_freshness(self, *states: EvidenceFreshnessState) -> EvidenceFreshnessState:
        order = {"unavailable": 0, "unknown": 1, "stale": 2, "fresh": 3}
        return sorted(states, key=lambda item: order.get(item, 99))[0] if states else "unknown"

    def _combine_freshness(self, states: list[EvidenceFreshnessState]) -> EvidenceFreshnessState:
        return self._merge_freshness(*states) if states else "unknown"

    def _combine_trust(self, states: list[DependencyGraphTrustState]) -> DependencyGraphTrustState:
        if not states:
            return "unknown"
        order = {
            "unavailable": 0,
            "conflicting": 1,
            "unknown": 2,
            "stale": 3,
            "partial": 4,
            "trusted_with_warning": 5,
            "trusted": 6,
        }
        return sorted(states, key=lambda item: order.get(item, 99))[0]

    def _dedupe_findings(self, findings: list[DependencyGraphFinding]) -> list[DependencyGraphFinding]:
        unique: dict[str, DependencyGraphFinding] = {}
        for finding in findings:
            unique[finding.finding_id] = finding
        return list(unique.values())


class _DependencyGraphIndex(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nodes: dict[str, DependencyGraphNode]
    edges: dict[str, DependencyGraphEdge]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _content_fingerprint(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _deterministic_id(prefix: str, payload: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"gaia:{prefix}:{_content_fingerprint(payload)}"))


def _dedupe_preserve_order(values: list[Any]) -> list[Any]:
    ordered: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _dedupe_provenance(values: list[ProgrammeProvenanceRecord]) -> list[ProgrammeProvenanceRecord]:
    ordered: list[ProgrammeProvenanceRecord] = []
    seen: set[str] = set()
    for value in values:
        fingerprint = _content_fingerprint(value.model_dump(mode="json"))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        ordered.append(value)
    return ordered
