from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field

from gaia.change_impact import ChangeImpactResult
from gaia.config import Settings
from gaia.dependency_graph import DependencyGraphCycleRecord, DependencyGraphService
from gaia.models import (
    ProjectChangeFinding,
    ProjectConfig,
    ProjectHealthSnapshot,
    ProjectRecommendation,
    WorkPackageRecord,
    utc_now,
)
from gaia.programme_registry import (
    ArchitectureRelationshipRecord,
    ProgrammeProvenanceRecord,
    ProjectContractRecord,
    ProjectContractService,
)
from gaia.project_health import ProjectHealthService
from gaia.recommendations import RecommendationService
from gaia.work_packages import WorkPackageService

ProgrammeRoadmapState = Literal[
    "NOW",
    "NEXT",
    "LATER",
    "BLOCKED",
    "WAITING_FOR_EVIDENCE",
    "RELEASE_CANDIDATE",
    "MAINTENANCE",
    "EXPERIMENT",
]
ProgrammeReadinessState = Literal["READY", "BLOCKED", "WAITING_FOR_EVIDENCE", "PARTIAL", "UNKNOWN"]
ProgrammeReleaseReadinessState = Literal[
    "READY",
    "READY_WITH_WARNINGS",
    "BLOCKED",
    "WAITING_FOR_EVIDENCE",
    "PARTIAL",
    "UNKNOWN",
]
ProgrammeHumanApprovalState = Literal["unknown", "required", "pending", "approved", "rejected"]
ProgrammeRoadmapSourceType = Literal[
    "recommendation",
    "work_package",
    "change_impact",
    "project_blocker",
    "maintenance_finding",
    "experiment_finding",
]
ProgrammeRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"]
ProgrammeTrustState = Literal[
    "trusted",
    "trusted_with_warning",
    "partial",
    "stale",
    "unknown",
    "conflicting",
    "unavailable",
]
ProgrammeValidationReferenceKind = Literal["test_command", "build_command", "documentation_root", "release_process_reference"]
ProgrammeRollbackRelationshipKind = Literal["must_rollback_together", "independent", "unknown"]
ProgrammeCompatibilityConstraintKind = Literal[
    "shared_release_process",
    "version_requirement",
    "dependency_order",
    "compatibility_window",
    "change_impact_constraint",
]

_ROADMAP_STATE_ORDER: dict[str, int] = {
    "BLOCKED": 0,
    "WAITING_FOR_EVIDENCE": 1,
    "RELEASE_CANDIDATE": 2,
    "NOW": 3,
    "NEXT": 4,
    "LATER": 5,
    "MAINTENANCE": 6,
    "EXPERIMENT": 7,
}
_FRESHNESS_ORDER: dict[str, int] = {"fresh": 0, "aging": 1, "stale": 2, "unknown": 3, "unavailable": 4}
_TRUST_ORDER: dict[str, int] = {
    "trusted": 0,
    "trusted_with_warning": 1,
    "partial": 2,
    "stale": 3,
    "unknown": 4,
    "conflicting": 5,
    "unavailable": 6,
}
_READINESS_ORDER: dict[str, int] = {"READY": 0, "PARTIAL": 1, "WAITING_FOR_EVIDENCE": 2, "BLOCKED": 3, "UNKNOWN": 4}
_RELEASE_READINESS_ORDER: dict[str, int] = {
    "READY": 0,
    "READY_WITH_WARNINGS": 1,
    "PARTIAL": 2,
    "WAITING_FOR_EVIDENCE": 3,
    "BLOCKED": 4,
    "UNKNOWN": 5,
}
_MAINTENANCE_CLASSES = {
    "release_drift",
    "contract_drift",
    "dependency_drift",
    "test_regression",
    "documentation_drift",
    "configuration_change",
}


class ProgrammeEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evidence_kind: str
    evidence_id: str | None = None
    description: str
    freshness: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProgrammeScoreFactor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    factor_id: str
    description: str
    value: int
    weight: int
    contribution: int
    evidence_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ProgrammeBlocker(BaseModel):
    model_config = ConfigDict(extra="ignore")

    blocker_id: str
    reason_code: str
    description: str
    source_kind: str
    source_id: str
    severity: Literal["info", "warning", "critical"] = "warning"
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    freshness: str = "unknown"
    trust: ProgrammeTrustState = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ProgrammeValidationReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    validation_id: str
    project_id: str
    reference_kind: ProgrammeValidationReferenceKind
    reference: str
    description: str
    source_id: str | None = None
    freshness: str = "unknown"
    trust: ProgrammeTrustState = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ProgrammeCompatibilityConstraint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    constraint_id: str
    constraint_kind: ProgrammeCompatibilityConstraintKind
    description: str
    source_project_id: str | None = None
    target_project_id: str | None = None
    required_value: str | None = None
    observed_value: str | None = None
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    freshness: str = "unknown"
    trust: ProgrammeTrustState = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ProgrammeRollbackRelationship(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rollback_relationship_id: str
    relationship_kind: ProgrammeRollbackRelationshipKind = "unknown"
    description: str
    source_project_id: str | None = None
    target_project_id: str | None = None
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    freshness: str = "unknown"
    trust: ProgrammeTrustState = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ProgrammeRoadmapItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    roadmap_item_id: str
    semantic_fingerprint: str
    evaluation_fingerprint: str = ""
    source_type: ProgrammeRoadmapSourceType
    source_id: str
    project_id: str
    title: str
    objective: str
    roadmap_state: ProgrammeRoadmapState = "LATER"
    rank: int = 0
    priority_score: int = 0
    deterministic_score_factors: list[ProgrammeScoreFactor] = Field(default_factory=list)
    blocking_reasons: list[ProgrammeBlocker] = Field(default_factory=list)
    dependency_reasons: list[str] = Field(default_factory=list)
    impact_reasons: list[str] = Field(default_factory=list)
    risk: ProgrammeRiskLevel = "UNKNOWN"
    readiness: ProgrammeReadinessState = "UNKNOWN"
    freshness: str = "unknown"
    trust: ProgrammeTrustState = "unknown"
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    recommended_predecessors: list[str] = Field(default_factory=list)
    recommended_successors: list[str] = Field(default_factory=list)
    release_train_candidate: bool = False
    human_priority_reference: str | None = None
    human_priority_weight: int = 0


class ProgrammeRoadmapPortfolio(BaseModel):
    model_config = ConfigDict(extra="ignore")

    generated_at: datetime = Field(default_factory=utc_now)
    roadmap_items: list[ProgrammeRoadmapItem] = Field(default_factory=list)
    counts_by_state: dict[str, int] = Field(default_factory=dict)
    roadmap_fingerprint: str = ""


class ReleaseTrainParticipant(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: str
    project_name: str
    order: int = 0
    current_version: str | None = None
    release_channel: str | None = None
    release_process_reference: str | None = None
    readiness: ProgrammeReadinessState = "UNKNOWN"
    freshness: str = "unknown"
    trust: ProgrammeTrustState = "unknown"
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)


class ReleaseTrainVersionRequirement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirement_id: str
    project_id: str
    version: str | None = None
    release_channel: str | None = None
    release_process_reference: str | None = None
    contract_id: str | None = None
    contract_revision_id: str | None = None
    freshness: str = "unknown"
    trust: ProgrammeTrustState = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)


class ReleaseTrainRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    release_train_id: str
    objective: str
    semantic_fingerprint: str
    train_fingerprint: str = ""
    participating_projects: list[ReleaseTrainParticipant] = Field(default_factory=list)
    required_versions: list[ReleaseTrainVersionRequirement] = Field(default_factory=list)
    dependency_order: list[str] = Field(default_factory=list)
    compatibility_constraints: list[ProgrammeCompatibilityConstraint] = Field(default_factory=list)
    blocking_evidence: list[ProgrammeBlocker] = Field(default_factory=list)
    required_tests: list[ProgrammeValidationReference] = Field(default_factory=list)
    rollback_relationships: list[ProgrammeRollbackRelationship] = Field(default_factory=list)
    release_readiness: ProgrammeReleaseReadinessState = "UNKNOWN"
    human_approval_state: ProgrammeHumanApprovalState = "required"
    freshness: str = "unknown"
    trust: ProgrammeTrustState = "unknown"
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)


class ReleaseTrainPortfolio(BaseModel):
    model_config = ConfigDict(extra="ignore")

    generated_at: datetime = Field(default_factory=utc_now)
    release_trains: list[ReleaseTrainRecord] = Field(default_factory=list)
    counts_by_readiness: dict[str, int] = Field(default_factory=dict)
    release_train_fingerprint: str = ""


@dataclass(slots=True)
class _ProgrammeProjectContext:
    project: ProjectConfig
    contract: ProjectContractRecord | None
    health: ProjectHealthSnapshot | None
    recommendations: list[ProjectRecommendation]
    work_packages: list[WorkPackageRecord]
    findings: list[ProjectChangeFinding]
    dependency_projects: list[str]
    dependent_projects: list[str]
    human_priority_reference: str | None
    human_priority_weight: int


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _content_fingerprint(value: Any) -> str:
    return _sha256_text(_json_dumps(value))


def _stable_fingerprint_value(value: Any) -> Any:
    volatile_keys = {"captured_at", "audit_event_id", "event_id", "health_snapshot_id"}
    if isinstance(value, dict):
        return {
            key: _stable_fingerprint_value(item)
            for key, item in value.items()
            if key not in volatile_keys
        }
    if isinstance(value, list):
        return [_stable_fingerprint_value(item) for item in value]
    if isinstance(value, tuple):
        return [_stable_fingerprint_value(item) for item in value]
    return value


def _deterministic_id(prefix: str, payload: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"gaia:{prefix}:{_content_fingerprint(payload)}"))


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _combine_freshness(values: Iterable[str]) -> str:
    ordered = [value for value in values if value]
    if not ordered:
        return "unknown"
    return max(ordered, key=lambda item: _FRESHNESS_ORDER.get(item, 99))


def _combine_trust(values: Iterable[str]) -> ProgrammeTrustState:
    ordered = [value for value in values if value]
    if not ordered:
        return "unknown"
    return cast(ProgrammeTrustState, max(ordered, key=lambda item: _TRUST_ORDER.get(item, 99)))


def _trust_from_freshness(freshness: str) -> ProgrammeTrustState:
    if freshness == "fresh":
        return "trusted"
    if freshness == "aging":
        return "trusted_with_warning"
    if freshness == "stale":
        return "stale"
    if freshness == "unavailable":
        return "unavailable"
    return "unknown"


def _risk_from_score(score: int) -> ProgrammeRiskLevel:
    if score >= 90:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    if score >= 0:
        return "LOW"
    return "UNKNOWN"


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _project_human_priority(project: ProjectConfig) -> tuple[str | None, int]:
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    reference = _normalize_optional_text(
        metadata.get("human_priority_reference")
        or metadata.get("human_priority")
        or metadata.get("programme_priority_reference")
    )
    weight = 0
    candidate = metadata.get("human_priority_weight") or metadata.get("programme_priority_weight")
    if isinstance(candidate, (int, float)):
        weight = int(candidate)
    elif isinstance(metadata.get("human_priority"), int):
        weight = int(metadata["human_priority"])
    elif isinstance(reference, str) and reference.isdigit():
        weight = int(reference)
        reference = None
    return reference, weight


def _project_entity_id(project_id: str) -> str:
    return f"architecture-entity:project:{project_id}"


def _project_contract_freshness(contract: ProjectContractRecord | None) -> str:
    return contract.freshness_state if contract is not None else "unknown"


def _project_health_freshness(health: ProjectHealthSnapshot | None) -> str:
    if health is None:
        return "unknown"
    return str(health.normalized_payload.get("configured_evidence", {}).get("evidence_freshness", {}).get("state", "unknown"))


def _stable_project_health_identity(project_id: str, health: ProjectHealthSnapshot) -> str:
    return _content_fingerprint(
        _stable_fingerprint_value(
            {
                "project_id": project_id,
                "normalized_status": health.normalized_status,
                "reason_codes": list(health.reason_codes),
                "explanations": list(health.explanations),
                "blocking_conditions": list(health.blocking_conditions),
                "attention_conditions": list(health.attention_conditions),
                "unknown_fields": list(health.unknown_fields),
            }
        )
    )


class ProgrammeRoadmapService:
    def __init__(
        self,
        settings: Settings,
        project_contract_service: ProjectContractService,
        project_health_service: ProjectHealthService,
        recommendation_service: RecommendationService,
        work_package_service: WorkPackageService,
        dependency_graph_service: DependencyGraphService,
    ) -> None:
        self.settings = settings
        self.project_contract_service = project_contract_service
        self.project_health_service = project_health_service
        self.recommendation_service = recommendation_service
        self.work_package_service = work_package_service
        self.dependency_graph_service = dependency_graph_service

    def roadmap_view(self, *, change_impact_results: Iterable[ChangeImpactResult] | None = None) -> ProgrammeRoadmapPortfolio:
        contexts = self._project_contexts()
        release_groups, release_readiness_by_project = self._discover_release_groups_and_readiness(contexts, change_impact_results)
        items: list[ProgrammeRoadmapItem] = []

        for context in contexts:
            items.extend(self._items_from_project_blockers(context, release_readiness_by_project))
            items.extend(self._items_from_recommendations(context, release_readiness_by_project))
            items.extend(self._items_from_work_packages(context, release_readiness_by_project))
            items.extend(self._items_from_findings(context, release_readiness_by_project))
            items.extend(self._items_from_change_impacts(context, change_impact_results, release_readiness_by_project))
            items.extend(self._items_from_explicit_mode(context, release_readiness_by_project))

        self._apply_release_train_candidate_flags(items, release_groups, release_readiness_by_project)
        items = self._finalize_items(items)
        portfolio = ProgrammeRoadmapPortfolio(
            generated_at=utc_now(),
            roadmap_items=items,
            counts_by_state=dict(sorted(Counter(item.roadmap_state for item in items).items(), key=lambda item: _ROADMAP_STATE_ORDER.get(item[0], 99))),
        )
        portfolio.roadmap_fingerprint = _content_fingerprint(_stable_fingerprint_value(self._roadmap_payload(portfolio)))
        return portfolio

    def _project_contexts(self) -> list[_ProgrammeProjectContext]:
        contexts: list[_ProgrammeProjectContext] = []
        for project in sorted(self.settings.projects.values(), key=lambda item: item.project_id):
            if not project.enabled:
                continue
            contract = self.project_contract_service.current_approved_contract(project.project_id)
            health = self.project_health_service.latest_project_health_snapshot(project.project_id)
            recommendations = self.recommendation_service.list_project_recommendations(project.project_id)
            work_packages = self.work_package_service.list_work_packages(project_id=project.project_id)
            findings = self.project_health_service.database.latest_project_change_findings(project.project_id)
            dependencies = [item.target_project_id for item in self.dependency_graph_service.project_dependencies(project.project_id, transitive=True)]
            dependents = [item.source_project_id for item in self.dependency_graph_service.project_dependents(project.project_id, transitive=True)]
            human_priority_reference, human_priority_weight = _project_human_priority(project)
            contexts.append(
                _ProgrammeProjectContext(
                    project=project,
                    contract=contract,
                    health=health,
                    recommendations=recommendations,
                    work_packages=work_packages,
                    findings=findings,
                    dependency_projects=_dedupe_preserve_order(dependencies),
                    dependent_projects=_dedupe_preserve_order(dependents),
                    human_priority_reference=human_priority_reference,
                    human_priority_weight=human_priority_weight,
                )
            )
        return contexts

    def _discover_release_groups_and_readiness(
        self,
        contexts: list[_ProgrammeProjectContext],
        change_impact_results: Iterable[ChangeImpactResult] | None,
    ) -> tuple[list[list[str]], dict[str, ProgrammeReleaseReadinessState]]:
        adjacency: dict[str, set[str]] = defaultdict(set)
        release_readiness: dict[str, ProgrammeReleaseReadinessState] = {}
        change_impacts = list(change_impact_results or [])
        by_release_reference: dict[str, set[str]] = defaultdict(set)
        project_ids = {context.project.project_id for context in contexts}
        for context in contexts:
            project_id = context.project.project_id
            release_readiness[project_id] = self._project_release_readiness(context)
            contract = context.contract
            if contract is not None:
                revision = contract.current_revision
                if revision is not None and revision.content.release_process_reference:
                    by_release_reference[revision.content.release_process_reference].add(project_id)
        for participants in by_release_reference.values():
            ordered = sorted(participants)
            for index, project_id in enumerate(ordered):
                for other in ordered[index + 1 :]:
                    adjacency[project_id].add(other)
                    adjacency[other].add(project_id)
        for impact in change_impacts:
            affected_projects = [item.project_id for item in impact.affected_projects if item.project_id in project_ids]
            if len(affected_projects) < 2:
                continue
            ordered = sorted(_dedupe_preserve_order(affected_projects))
            for index, project_id in enumerate(ordered):
                for other in ordered[index + 1 :]:
                    adjacency[project_id].add(other)
                    adjacency[other].add(project_id)
        for context in contexts:
            project_id = context.project.project_id
            for dependent in context.dependency_projects:
                if dependent in project_ids and release_readiness.get(dependent) != "UNKNOWN":
                    adjacency[project_id].add(dependent)
                    adjacency[dependent].add(project_id)
            for dependent in context.dependent_projects:
                if dependent in project_ids and release_readiness.get(dependent) != "UNKNOWN":
                    adjacency[project_id].add(dependent)
                    adjacency[dependent].add(project_id)
        groups = self._connected_components(adjacency, project_ids)
        return groups, release_readiness

    def _connected_components(self, adjacency: dict[str, set[str]], project_ids: set[str]) -> list[list[str]]:
        remaining = set(project_ids)
        groups: list[list[str]] = []
        while remaining:
            start = min(remaining)
            remaining.remove(start)
            queue = deque([start])
            component = {start}
            while queue:
                project_id = queue.popleft()
                for other in sorted(adjacency.get(project_id, set())):
                    if other in remaining:
                        remaining.remove(other)
                        component.add(other)
                        queue.append(other)
            if len(component) > 1:
                groups.append(sorted(component))
        return sorted(groups, key=lambda item: (len(item), item))

    def _project_release_readiness(self, context: _ProgrammeProjectContext) -> ProgrammeReleaseReadinessState:
        contract = context.contract
        health = context.health
        if contract is None or contract.current_revision is None:
            return "WAITING_FOR_EVIDENCE"
        if health is None:
            return "WAITING_FOR_EVIDENCE"
        if health.normalized_status == "blocked":
            return "BLOCKED"
        freshness = _project_health_freshness(health)
        if freshness in {"stale", "unknown", "unavailable"}:
            return "WAITING_FOR_EVIDENCE"
        if health.normalized_status == "attention":
            return "PARTIAL"
        if contract.status != "approved":
            return "BLOCKED"
        if contract.current_revision.freshness_state in {"stale", "unknown"}:
            return "WAITING_FOR_EVIDENCE"
        return "READY"

    def _items_from_project_blockers(
        self,
        context: _ProgrammeProjectContext,
        release_readiness_by_project: dict[str, ProgrammeReleaseReadinessState],
    ) -> list[ProgrammeRoadmapItem]:
        items: list[ProgrammeRoadmapItem] = []
        health = context.health
        if health is None:
            return items
        if health.normalized_status not in {"blocked", "attention", "unknown"} and not health.blocking_conditions:
            return items
        source_type: ProgrammeRoadmapSourceType = "project_blocker"
        base_state = "BLOCKED" if health.normalized_status == "blocked" else "WAITING_FOR_EVIDENCE" if health.normalized_status == "unknown" else "NEXT"
        blocker_severity: Literal["info", "warning", "critical"] = "critical" if health.normalized_status == "blocked" else "warning"
        evidence_refs = self._project_health_evidence_refs(context.project.project_id, health)
        blockers = [
            ProgrammeBlocker(
                blocker_id=_deterministic_id(
                    "roadmap-blocker",
                    {"project_id": context.project.project_id, "source_id": _stable_project_health_identity(context.project.project_id, health), "reason": reason},
                ),
                reason_code=reason,
                description=reason.replace("_", " "),
                source_kind="project_health",
                source_id=_stable_project_health_identity(context.project.project_id, health),
                severity=blocker_severity,
                evidence_refs=evidence_refs,
                freshness=_project_health_freshness(health),
                trust=_trust_from_freshness(_project_health_freshness(health)),
                details={"normalized_status": health.normalized_status},
            )
            for reason in (health.reason_codes or ["project_health_attention"])
        ]
        item = self._build_roadmap_item(
            context,
            source_type=source_type,
            source_id=_stable_project_health_identity(context.project.project_id, health),
            title=f"Project health for {context.project.name}",
            objective=health.explanations[0] if health.explanations else "Review the current project-health blockers.",
            state_hint=cast(ProgrammeRoadmapState, base_state),
            blockers=blockers,
            evidence_refs=evidence_refs,
            risk=_risk_from_score(60 if health.normalized_status == "blocked" else 35),
            readiness="BLOCKED" if health.normalized_status == "blocked" else "WAITING_FOR_EVIDENCE" if health.normalized_status == "unknown" else "PARTIAL",
            freshness=_project_health_freshness(health),
            trust=_trust_from_freshness(_project_health_freshness(health)),
            factor_seed={"kind": "project_health", "status": health.normalized_status, "reasons": list(health.reason_codes)},
            dependency_reasons=[f"Project health status is {health.normalized_status}."],
            impact_reasons=list(health.attention_conditions or health.blocking_conditions or []),
            release_train_candidate=release_readiness_by_project.get(context.project.project_id) in {"READY", "READY_WITH_WARNINGS"},
        )
        items.append(item)
        return items

    def _items_from_recommendations(
        self,
        context: _ProgrammeProjectContext,
        release_readiness_by_project: dict[str, ProgrammeReleaseReadinessState],
    ) -> list[ProgrammeRoadmapItem]:
        items: list[ProgrammeRoadmapItem] = []
        for recommendation in context.recommendations:
            if recommendation.lifecycle_state not in {"active", "blocked"}:
                continue
            freshness = recommendation.evidence_freshness
            trust = _trust_from_freshness(freshness)
            blockers = [
                ProgrammeBlocker(
                    blocker_id=_deterministic_id(
                        "roadmap-blocker",
                        {"project_id": context.project.project_id, "source_id": recommendation.recommendation_id, "reason": blocker.blocker_type},
                    ),
                    reason_code=blocker.blocker_type,
                    description=blocker.blocker_description,
                    source_kind="recommendation",
                    source_id=recommendation.recommendation_id,
                    severity="critical" if blocker.blocker_type in {"evidence_too_stale", "higher_order_condition_unresolved"} else "warning",
                    evidence_refs=self._evidence_refs_from_recommendation(recommendation),
                    freshness=freshness,
                    trust=trust,
                    details={"required_condition": blocker.required_condition, "evidence_ids": list(blocker.evidence_ids)},
                )
                for blocker in recommendation.blockers
            ]
            readiness = self._recommendation_readiness(recommendation, blockers)
            state_hint = "BLOCKED" if readiness == "BLOCKED" else "WAITING_FOR_EVIDENCE" if readiness == "WAITING_FOR_EVIDENCE" else "NEXT"
            item = self._build_roadmap_item(
                context,
                source_type="recommendation",
                source_id=recommendation.recommendation_id,
                title=recommendation.title or f"Recommendation {recommendation.recommendation_type}",
                objective=recommendation.concise_summary or recommendation.rationale or recommendation.why_it_matters,
                state_hint=cast(ProgrammeRoadmapState, state_hint),
                blockers=blockers,
                evidence_refs=self._evidence_refs_from_recommendation(recommendation),
                risk=_risk_from_score(recommendation.deterministic_score),
                readiness=readiness,
                freshness=freshness,
                trust=trust,
                factor_seed={
                    "kind": "recommendation",
                    "type": recommendation.recommendation_type,
                    "priority": recommendation.priority_tier,
                    "score": recommendation.deterministic_score,
                    "state": recommendation.lifecycle_state,
                },
                dependency_reasons=list(recommendation.dependencies),
                impact_reasons=list(recommendation.reasons_to_proceed or [recommendation.why_it_matters]),
                release_train_candidate=release_readiness_by_project.get(context.project.project_id) in {"READY", "READY_WITH_WARNINGS"},
                human_priority_reference=context.human_priority_reference,
                human_priority_weight=context.human_priority_weight,
            )
            items.append(item)
        return items

    def _items_from_work_packages(
        self,
        context: _ProgrammeProjectContext,
        release_readiness_by_project: dict[str, ProgrammeReleaseReadinessState],
    ) -> list[ProgrammeRoadmapItem]:
        items: list[ProgrammeRoadmapItem] = []
        for package in context.work_packages:
            freshness = package.staleness_state
            trust = _trust_from_freshness(freshness)
            blockers: list[ProgrammeBlocker] = []
            readiness: ProgrammeReadinessState = "READY"
            if package.approval_state in {"expired", "failed", "rolled_back"}:
                readiness = "BLOCKED"
                blockers.append(
                    ProgrammeBlocker(
                        blocker_id=_deterministic_id(
                            "roadmap-blocker",
                            {"project_id": context.project.project_id, "source_id": package.work_package_id, "reason": package.approval_state},
                        ),
                        reason_code=package.approval_state,
                        description=f"Work package is {package.approval_state}.",
                        source_kind="work_package",
                        source_id=package.work_package_id,
                        severity="critical",
                        freshness=freshness,
                        trust=trust,
                    )
                )
            elif freshness != "fresh":
                readiness = "WAITING_FOR_EVIDENCE"
                blockers.append(
                    ProgrammeBlocker(
                        blocker_id=_deterministic_id(
                            "roadmap-blocker",
                            {"project_id": context.project.project_id, "source_id": package.work_package_id, "reason": freshness},
                        ),
                        reason_code="stale_work_package",
                        description=f"Work package evidence is {freshness}.",
                        source_kind="work_package",
                        source_id=package.work_package_id,
                        severity="warning",
                        freshness=freshness,
                        trust=trust,
                    )
                )
            elif package.gate_state == "blocked":
                readiness = "BLOCKED"
                blockers.append(
                    ProgrammeBlocker(
                        blocker_id=_deterministic_id(
                            "roadmap-blocker",
                            {"project_id": context.project.project_id, "source_id": package.work_package_id, "reason": "gate_blocked"},
                        ),
                        reason_code="gate_blocked",
                        description="Work package gate is blocked.",
                        source_kind="work_package",
                        source_id=package.work_package_id,
                        severity="critical",
                        freshness=freshness,
                        trust=trust,
                    )
                )
            elif package.approval_state in {"approved", "handed_off"}:
                readiness = "READY"
            else:
                readiness = "PARTIAL" if package.approval_state == "under_review" else "READY"
            score_seed = {
                "kind": "work_package",
                "package_id": package.work_package_id,
                "approval_state": package.approval_state,
                "gate_state": package.gate_state,
                "risk": package.risk_classification,
                "staleness": package.staleness_state,
            }
            state_hint: ProgrammeRoadmapState = "NEXT" if readiness in {"READY", "PARTIAL"} else "BLOCKED"
            item = self._build_roadmap_item(
                context,
                source_type="work_package",
                source_id=package.work_package_id,
                title=package.title or f"Work package {package.work_package_id}",
                objective=package.objective or package.expected_outcome or package.reason,
                state_hint=state_hint,
                blockers=blockers,
                evidence_refs=self._evidence_refs_from_work_package(package),
                risk=cast(ProgrammeRiskLevel, package.risk_classification.upper() if package.risk_classification != "unknown" else "UNKNOWN"),
                readiness=readiness,
                freshness=freshness,
                trust=trust,
                factor_seed=score_seed,
                dependency_reasons=list(package.prerequisites or package.source_recommendation_dependencies),
                impact_reasons=list(package.affected_areas or package.in_scope_areas),
                release_train_candidate=release_readiness_by_project.get(context.project.project_id) in {"READY", "READY_WITH_WARNINGS"} and package.approval_state in {"approved", "handed_off"},
                human_priority_reference=context.human_priority_reference,
                human_priority_weight=context.human_priority_weight,
            )
            items.append(item)
        return items

    def _items_from_findings(
        self,
        context: _ProgrammeProjectContext,
        release_readiness_by_project: dict[str, ProgrammeReleaseReadinessState],
    ) -> list[ProgrammeRoadmapItem]:
        items: list[ProgrammeRoadmapItem] = []
        for finding in context.findings:
            if finding.change_class not in _MAINTENANCE_CLASSES:
                continue
            freshness = finding.confidence if finding.confidence in {"high", "medium", "low"} else "unknown"
            trust = "trusted" if finding.confidence == "high" else "trusted_with_warning" if finding.confidence == "medium" else "partial"
            blockers = [
                ProgrammeBlocker(
                    blocker_id=_deterministic_id(
                        "roadmap-blocker",
                        {"project_id": context.project.project_id, "source_id": finding.finding_id, "reason": finding.change_class},
                    ),
                    reason_code=finding.change_class,
                    description=finding.explanation or finding.change_class,
                    source_kind="maintenance_finding",
                    source_id=finding.finding_id,
                    severity="critical" if finding.severity == "critical" else "warning",
                    evidence_refs=self._evidence_refs_from_change_finding(finding),
                    freshness=freshness,
                    trust=cast(ProgrammeTrustState, trust),
                    details={"severity": finding.severity, "direction": finding.direction},
                )
            ]
            item = self._build_roadmap_item(
                context,
                source_type="maintenance_finding",
                source_id=finding.finding_id,
                title=finding.explanation or f"Maintenance finding {finding.change_class}",
                objective=finding.explanation or finding.change_class,
                state_hint="MAINTENANCE",
                blockers=blockers,
                evidence_refs=self._evidence_refs_from_change_finding(finding),
                risk="HIGH" if finding.severity == "critical" else "MEDIUM",
                readiness="PARTIAL" if finding.severity != "critical" else "BLOCKED",
                freshness=freshness,
                trust=cast(ProgrammeTrustState, trust),
                factor_seed={"kind": "maintenance_finding", "change_class": finding.change_class, "severity": finding.severity},
                dependency_reasons=[f"Change finding {finding.change_class} requires maintenance review."],
                impact_reasons=[finding.explanation or finding.change_class],
                release_train_candidate=False,
                human_priority_reference=context.human_priority_reference,
                human_priority_weight=context.human_priority_weight,
            )
            items.append(item)
        return items

    def _items_from_change_impacts(
        self,
        context: _ProgrammeProjectContext,
        change_impact_results: Iterable[ChangeImpactResult] | None,
        release_readiness_by_project: dict[str, ProgrammeReleaseReadinessState],
    ) -> list[ProgrammeRoadmapItem]:
        items: list[ProgrammeRoadmapItem] = []
        for impact in change_impact_results or []:
            if not any(project.project_id == context.project.project_id for project in impact.affected_projects):
                continue
            blockers: list[ProgrammeBlocker] = []
            for finding in impact.unknown_findings:
                blockers.append(
                    ProgrammeBlocker(
                        blocker_id=_deterministic_id(
                            "roadmap-blocker",
                            {"project_id": context.project.project_id, "source_id": impact.analysis_id, "reason": finding.finding_type},
                        ),
                        reason_code=finding.finding_type,
                        description=finding.explanation,
                        source_kind="change_impact",
                        source_id=impact.analysis_id,
                        severity=finding.severity,
                        evidence_refs=self._change_impact_evidence_refs(impact),
                        freshness=impact.freshness_state,
                        trust=cast(ProgrammeTrustState, impact.trust_state),
                        details={"finding_id": finding.finding_id},
                    )
                )
            readiness = "BLOCKED" if blockers and any(item.severity == "critical" for item in blockers) else "PARTIAL" if blockers else "READY"
            state_hint = "RELEASE_CANDIDATE" if impact.affected_releases and readiness == "READY" else "NOW"
            item = self._build_roadmap_item(
                context,
                source_type="change_impact",
                source_id=impact.analysis_id,
                title=impact.proposal.title,
                objective=impact.proposal.objective,
                state_hint=cast(ProgrammeRoadmapState, state_hint),
                blockers=blockers,
                evidence_refs=self._change_impact_evidence_refs(impact),
                risk=impact.risk.risk_level if impact.risk.risk_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "UNKNOWN",
                readiness=cast(ProgrammeReadinessState, readiness),
                freshness=impact.freshness_state,
                trust=cast(ProgrammeTrustState, impact.trust_state),
                factor_seed={
                    "kind": "change_impact",
                    "analysis_id": impact.analysis_id,
                    "risk": impact.risk.risk_level,
                    "affected_projects": [item.project_id for item in impact.affected_projects],
                    "affected_releases": [item.project_id for item in impact.affected_releases],
                },
                dependency_reasons=[f"Change impact analysis {impact.analysis_id}"],
                impact_reasons=[finding.explanation for finding in impact.unknown_findings] or [impact.risk.explanation],
                release_train_candidate=bool(impact.affected_releases) and release_readiness_by_project.get(context.project.project_id) in {"READY", "READY_WITH_WARNINGS"},
                human_priority_reference=context.human_priority_reference,
                human_priority_weight=context.human_priority_weight,
            )
            items.append(item)
        return items

    def _items_from_explicit_mode(
        self,
        context: _ProgrammeProjectContext,
        release_readiness_by_project: dict[str, ProgrammeReleaseReadinessState],
    ) -> list[ProgrammeRoadmapItem]:
        mode = _normalize_optional_text(context.project.metadata.get("programme_mode")) if isinstance(context.project.metadata, dict) else None
        if mode not in {"maintenance", "experiment"}:
            return []
        source_type = "maintenance_finding" if mode == "maintenance" else "experiment_finding"
        state_hint = "MAINTENANCE" if mode == "maintenance" else "EXPERIMENT"
        item = self._build_roadmap_item(
            context,
            source_type=cast(ProgrammeRoadmapSourceType, source_type),
            source_id=f"{context.project.project_id}:{mode}",
            title=f"{context.project.name} {mode} work",
            objective=f"Carry out explicit {mode} mode work recorded in project metadata.",
                state_hint=cast(ProgrammeRoadmapState, state_hint),
            blockers=[],
            evidence_refs=[],
            risk="LOW",
            readiness="READY",
            freshness="fresh",
            trust="trusted",
            factor_seed={"kind": "programme_mode", "mode": mode},
            dependency_reasons=[],
            impact_reasons=[],
            release_train_candidate=release_readiness_by_project.get(context.project.project_id) in {"READY", "READY_WITH_WARNINGS"},
            human_priority_reference=context.human_priority_reference,
            human_priority_weight=context.human_priority_weight,
        )
        return [item]

    def _apply_release_train_candidate_flags(
        self,
        items: list[ProgrammeRoadmapItem],
        release_groups: list[list[str]],
        release_readiness_by_project: dict[str, ProgrammeReleaseReadinessState],
    ) -> None:
        train_projects = {project_id for group in release_groups if len(group) > 1 for project_id in group}
        for item in items:
            if item.project_id in train_projects and release_readiness_by_project.get(item.project_id) in {"READY", "READY_WITH_WARNINGS"}:
                item.release_train_candidate = True

    def _finalize_items(self, items: list[ProgrammeRoadmapItem]) -> list[ProgrammeRoadmapItem]:
        scored_items: list[ProgrammeRoadmapItem] = []
        for item in items:
            item.priority_score = self._score_item(item)
            item.roadmap_state = self._assign_state(item)
            item.evaluation_fingerprint = _content_fingerprint(
                _stable_fingerprint_value(
                {
                    "semantic_fingerprint": item.semantic_fingerprint,
                    "roadmap_state": item.roadmap_state,
                    "priority_score": item.priority_score,
                    "risk": item.risk,
                    "readiness": item.readiness,
                    "freshness": item.freshness,
                    "trust": item.trust,
                    "release_train_candidate": item.release_train_candidate,
                    "blocking_reasons": [blocker.model_dump(mode="json") for blocker in item.blocking_reasons],
                    "score_factors": [factor.model_dump(mode="json") for factor in item.deterministic_score_factors],
                }
                )
            )
            scored_items.append(item)
        scored_items.sort(
            key=lambda item: (
                _ROADMAP_STATE_ORDER.get(item.roadmap_state, 99),
                -item.priority_score,
                item.project_id,
                item.source_type,
                item.source_id,
                item.roadmap_item_id,
            )
        )
        for index, item in enumerate(scored_items, start=1):
            item.rank = index
        return scored_items

    def _assign_state(self, item: ProgrammeRoadmapItem) -> ProgrammeRoadmapState:
        if item.blocking_reasons and any(blocker.severity == "critical" for blocker in item.blocking_reasons):
            return "BLOCKED"
        if item.readiness == "BLOCKED":
            return "BLOCKED"
        if item.readiness == "WAITING_FOR_EVIDENCE":
            return "WAITING_FOR_EVIDENCE"
        if item.source_type == "maintenance_finding":
            return "MAINTENANCE"
        if item.source_type == "experiment_finding":
            return "EXPERIMENT"
        if item.release_train_candidate and item.readiness in {"READY", "PARTIAL"} and item.priority_score >= 60:
            return "RELEASE_CANDIDATE"
        if item.priority_score >= 80:
            return "NOW"
        if item.priority_score >= 50:
            return "NEXT"
        return "LATER"

    def _score_item(self, item: ProgrammeRoadmapItem) -> int:
        score = 0
        factors = self._score_factors_for_item(item)
        item.deterministic_score_factors = factors
        for factor in factors:
            score += factor.contribution
        return score

    def _score_factors_for_item(self, item: ProgrammeRoadmapItem) -> list[ProgrammeScoreFactor]:
        freshness_weight = {"fresh": 0, "aging": 4, "stale": 15, "unknown": 18, "unavailable": 18}.get(item.freshness, 12)
        readiness_weight = {"READY": 18, "PARTIAL": 10, "WAITING_FOR_EVIDENCE": 4, "BLOCKED": 0, "UNKNOWN": 2}.get(item.readiness, 0)
        release_weight = 12 if item.release_train_candidate else 0
        base_weight = {
            "recommendation": 25,
            "work_package": 28,
            "change_impact": 30,
            "project_blocker": 40,
            "maintenance_finding": 18,
            "experiment_finding": 8,
        }.get(item.source_type, 10)
        state_weight = {
            "BLOCKED": 30,
            "WAITING_FOR_EVIDENCE": 20,
            "RELEASE_CANDIDATE": 25,
            "NOW": 22,
            "NEXT": 12,
            "LATER": 6,
            "MAINTENANCE": 10,
            "EXPERIMENT": 4,
        }.get(item.roadmap_state, 0)
        factors = [
            ProgrammeScoreFactor(
                factor_id=_deterministic_id("roadmap-factor", {"roadmap_item_id": item.roadmap_item_id, "name": "base"}),
                description="Base score by source type.",
                value=1,
                weight=base_weight,
                contribution=base_weight,
                details={"source_type": item.source_type},
            ),
            ProgrammeScoreFactor(
                factor_id=_deterministic_id("roadmap-factor", {"roadmap_item_id": item.roadmap_item_id, "name": "readiness"}),
                description="Readiness contribution.",
                value=1,
                weight=readiness_weight,
                contribution=readiness_weight,
                details={"readiness": item.readiness},
            ),
            ProgrammeScoreFactor(
                factor_id=_deterministic_id("roadmap-factor", {"roadmap_item_id": item.roadmap_item_id, "name": "freshness"}),
                description="Evidence freshness contribution.",
                value=1,
                weight=freshness_weight,
                contribution=freshness_weight,
                details={"freshness": item.freshness},
            ),
            ProgrammeScoreFactor(
                factor_id=_deterministic_id("roadmap-factor", {"roadmap_item_id": item.roadmap_item_id, "name": "release"}),
                description="Release-train coordination contribution.",
                value=1,
                weight=release_weight,
                contribution=release_weight,
                details={"release_train_candidate": item.release_train_candidate},
            ),
            ProgrammeScoreFactor(
                factor_id=_deterministic_id("roadmap-factor", {"roadmap_item_id": item.roadmap_item_id, "name": "state"}),
                description="State-specific boost.",
                value=1,
                weight=state_weight,
                contribution=state_weight,
                details={"roadmap_state": item.roadmap_state},
            ),
            ProgrammeScoreFactor(
                factor_id=_deterministic_id("roadmap-factor", {"roadmap_item_id": item.roadmap_item_id, "name": "human_priority"}),
                description="Explicit human-priority signal.",
                value=item.human_priority_weight,
                weight=1,
                contribution=item.human_priority_weight,
                details={"human_priority_reference": item.human_priority_reference},
            ),
            ProgrammeScoreFactor(
                factor_id=_deterministic_id("roadmap-factor", {"roadmap_item_id": item.roadmap_item_id, "name": "dependency"}),
                description="Dependency and impact breadth.",
                value=len(item.dependency_reasons) + len(item.impact_reasons),
                weight=2,
                contribution=(len(item.dependency_reasons) + len(item.impact_reasons)) * 2,
                details={"dependency_count": len(item.dependency_reasons), "impact_count": len(item.impact_reasons)},
            ),
        ]
        return factors

    def _build_roadmap_item(
        self,
        context: _ProgrammeProjectContext,
        *,
        source_type: ProgrammeRoadmapSourceType,
        source_id: str,
        title: str,
        objective: str,
        state_hint: ProgrammeRoadmapState,
        blockers: list[ProgrammeBlocker],
        evidence_refs: list[ProgrammeEvidenceReference],
        risk: ProgrammeRiskLevel,
        readiness: ProgrammeReadinessState,
        freshness: str,
        trust: ProgrammeTrustState,
        factor_seed: dict[str, Any],
        dependency_reasons: list[str],
        impact_reasons: list[str],
        release_train_candidate: bool,
        human_priority_reference: str | None = None,
        human_priority_weight: int = 0,
    ) -> ProgrammeRoadmapItem:
        semantic_fingerprint = _content_fingerprint(
            {
                "source_type": source_type,
                "source_id": source_id,
                "project_id": context.project.project_id,
            }
        )
        item = ProgrammeRoadmapItem(
            roadmap_item_id=_deterministic_id(
                "roadmap-item",
                {"source_type": source_type, "source_id": source_id, "project_id": context.project.project_id},
            ),
            semantic_fingerprint=semantic_fingerprint,
            source_type=source_type,
            source_id=source_id,
            project_id=context.project.project_id,
            title=title.strip() or source_id,
            objective=objective.strip() or title.strip() or source_id,
            roadmap_state=state_hint,
            blocking_reasons=blockers,
            dependency_reasons=_dedupe_preserve_order(dependency_reasons),
            impact_reasons=_dedupe_preserve_order(impact_reasons),
            risk=risk,
            readiness=readiness,
            freshness=freshness or "unknown",
            trust=trust,
            evidence_refs=evidence_refs,
            provenance=self._provenance_for_context(context, source_type=source_type, source_id=source_id, factor_seed=factor_seed),
            recommended_predecessors=_dedupe_preserve_order(context.dependency_projects),
            recommended_successors=_dedupe_preserve_order(context.dependent_projects),
            release_train_candidate=release_train_candidate,
            human_priority_reference=human_priority_reference,
            human_priority_weight=human_priority_weight,
        )
        return item

    def _provenance_for_context(
        self,
        context: _ProgrammeProjectContext,
        *,
        source_type: ProgrammeRoadmapSourceType,
        source_id: str,
        factor_seed: dict[str, Any],
    ) -> ProgrammeProvenanceRecord:
        provenance = ProgrammeProvenanceRecord(
            source_project_id=context.project.project_id,
            repository=str(context.project.root),
            canonical_gaia_source="gaia",
            source_document=source_id,
            evidence_reference=source_id,
            details={"source_type": source_type, **factor_seed},
        )
        if context.contract is not None:
            provenance.details["contract_id"] = context.contract.contract_id
        if context.health is not None:
            provenance.details["health_snapshot_id"] = _stable_project_health_identity(context.project.project_id, context.health)
        return provenance

    def _roadmap_payload(self, portfolio: ProgrammeRoadmapPortfolio) -> dict[str, Any]:
        return {
            "roadmap_items": [item.model_dump(mode="json") for item in portfolio.roadmap_items],
            "counts_by_state": portfolio.counts_by_state,
        }

    def _project_health_evidence_refs(
        self,
        project_id: str,
        health: ProjectHealthSnapshot,
    ) -> list[ProgrammeEvidenceReference]:
        return [
            ProgrammeEvidenceReference(
                evidence_kind="project_health_snapshot",
                evidence_id=_stable_project_health_identity(project_id, health),
                description=f"Latest project-health snapshot for {project_id}.",
                freshness=_project_health_freshness(health),
                details={"normalized_status": health.normalized_status},
            ),
            ProgrammeEvidenceReference(
                evidence_kind="project_health_condition",
                evidence_id=f"{project_id}:{health.normalized_status}",
                description=f"Project health status is {health.normalized_status}.",
                freshness=_project_health_freshness(health),
                details={"blocking_conditions": list(health.blocking_conditions), "attention_conditions": list(health.attention_conditions)},
            )
        ]

    def _evidence_refs_from_recommendation(self, recommendation: ProjectRecommendation) -> list[ProgrammeEvidenceReference]:
        refs = [
            ProgrammeEvidenceReference(
                evidence_kind=reference.evidence_kind,
                evidence_id=reference.evidence_id,
                description=reference.description,
                freshness=reference.freshness,
                details=dict(reference.details),
            )
            for reference in recommendation.evidence_references
        ]
        refs.append(
            ProgrammeEvidenceReference(
                evidence_kind="recommendation",
                evidence_id=recommendation.recommendation_id,
                description=recommendation.title or recommendation.recommendation_type,
                freshness=recommendation.evidence_freshness,
                details={
                    "priority_tier": recommendation.priority_tier,
                    "lifecycle_state": recommendation.lifecycle_state,
                    "policy_version": recommendation.recommendation_policy_version,
                },
            )
        )
        return refs

    def _evidence_refs_from_work_package(self, package: WorkPackageRecord) -> list[ProgrammeEvidenceReference]:
        refs = [
            ProgrammeEvidenceReference(
                evidence_kind="work_package",
                evidence_id=package.work_package_id,
                description=package.title or package.objective,
                freshness=package.staleness_state,
                details={"approval_state": package.approval_state, "gate_state": package.gate_state},
            )
        ]
        refs.extend(
            ProgrammeEvidenceReference(
                evidence_kind="work_package_revision",
                evidence_id=package.current_revision_id,
                description=f"Work package revision {package.current_revision_number}",
                freshness=package.staleness_state,
                details={"revision_number": package.current_revision_number},
            )
            for _ in [0]
            if package.current_revision_id is not None
        )
        return refs

    def _evidence_refs_from_change_finding(self, finding: ProjectChangeFinding) -> list[ProgrammeEvidenceReference]:
        return [
            ProgrammeEvidenceReference(
                evidence_kind="project_change_finding",
                evidence_id=finding.finding_id,
                description=finding.explanation or finding.change_class,
                freshness="fresh",
                details={"change_class": finding.change_class, "severity": finding.severity, "direction": finding.direction},
            )
        ]

    def _change_impact_evidence_refs(self, impact: ChangeImpactResult) -> list[ProgrammeEvidenceReference]:
        refs = [
            ProgrammeEvidenceReference(
                evidence_kind="change_impact",
                evidence_id=impact.analysis_id,
                description=impact.proposal.title,
                freshness=impact.freshness_state,
                details={"risk": impact.risk.risk_level, "proposal_id": impact.proposal_id},
            )
        ]
        for validation in impact.validation_references:
            refs.append(
                ProgrammeEvidenceReference(
                    evidence_kind=f"validation:{validation.reference_kind}",
                    evidence_id=validation.validation_id,
                    description=validation.description,
                    freshness=validation.freshness_state,
                    details={"reference": validation.reference},
                )
            )
        return refs

    def _recommendation_readiness(self, recommendation: ProjectRecommendation, blockers: list[ProgrammeBlocker]) -> ProgrammeReadinessState:
        if blockers and any(blocker.severity == "critical" for blocker in blockers):
            return "BLOCKED"
        if recommendation.lifecycle_state == "blocked":
            return "BLOCKED"
        if recommendation.evidence_freshness in {"stale", "unknown"}:
            return "WAITING_FOR_EVIDENCE"
        if recommendation.lifecycle_state == "deferred":
            return "PARTIAL"
        return "READY"


class ReleaseTrainService:
    def __init__(
        self,
        settings: Settings,
        project_contract_service: ProjectContractService,
        project_health_service: ProjectHealthService,
        dependency_graph_service: DependencyGraphService,
    ) -> None:
        self.settings = settings
        self.project_contract_service = project_contract_service
        self.project_health_service = project_health_service
        self.dependency_graph_service = dependency_graph_service

    def release_trains(
        self,
        *,
        change_impact_results: Iterable[ChangeImpactResult] | None = None,
    ) -> ReleaseTrainPortfolio:
        contexts = self._project_contexts()
        change_impacts = list(change_impact_results or [])
        release_groups = self._discover_release_groups(contexts, change_impacts)
        trains: list[ReleaseTrainRecord] = []
        for group in release_groups:
            train = self._build_release_train(group, contexts, change_impacts)
            if train is not None:
                trains.append(train)
        trains = sorted(trains, key=lambda item: (len(item.participating_projects), item.release_train_id))
        portfolio = ReleaseTrainPortfolio(
            generated_at=utc_now(),
            release_trains=trains,
            counts_by_readiness=dict(sorted(Counter(train.release_readiness for train in trains).items(), key=lambda item: _RELEASE_READINESS_ORDER.get(item[0], 99))),
        )
        portfolio.release_train_fingerprint = _content_fingerprint(_stable_fingerprint_value(self._portfolio_payload(portfolio)))
        return portfolio

    def _project_contexts(self) -> list[_ProgrammeProjectContext]:
        contexts: list[_ProgrammeProjectContext] = []
        for project in sorted(self.settings.projects.values(), key=lambda item: item.project_id):
            if not project.enabled:
                continue
            contract = self.project_contract_service.current_approved_contract(project.project_id)
            health = self.project_health_service.latest_project_health_snapshot(project.project_id)
            recommendations: list[ProjectRecommendation] = []
            work_packages: list[WorkPackageRecord] = []
            findings = self.project_health_service.database.latest_project_change_findings(project.project_id)
            dependencies = [item.target_project_id for item in self.dependency_graph_service.project_dependencies(project.project_id, transitive=True)]
            dependents = [item.source_project_id for item in self.dependency_graph_service.project_dependents(project.project_id, transitive=True)]
            human_priority_reference, human_priority_weight = _project_human_priority(project)
            contexts.append(
                _ProgrammeProjectContext(
                    project=project,
                    contract=contract,
                    health=health,
                    recommendations=recommendations,
                    work_packages=work_packages,
                    findings=findings,
                    dependency_projects=_dedupe_preserve_order(dependencies),
                    dependent_projects=_dedupe_preserve_order(dependents),
                    human_priority_reference=human_priority_reference,
                    human_priority_weight=human_priority_weight,
                )
            )
        return contexts

    def _discover_release_groups(
        self,
        contexts: list[_ProgrammeProjectContext],
        change_impact_results: list[ChangeImpactResult],
    ) -> list[list[str]]:
        project_ids = {context.project.project_id for context in contexts}
        adjacency: dict[str, set[str]] = defaultdict(set)
        release_reference_groups: dict[str, set[str]] = defaultdict(set)
        for context in contexts:
            contract = context.contract
            if contract is None or contract.current_revision is None:
                continue
            release_reference = contract.current_revision.content.release_process_reference
            if release_reference:
                release_reference_groups[release_reference].add(context.project.project_id)
        for group in release_reference_groups.values():
            ordered = sorted(group)
            for index, project_id in enumerate(ordered):
                for other in ordered[index + 1 :]:
                    adjacency[project_id].add(other)
                    adjacency[other].add(project_id)
        for relationship in self._release_relationships():
            source_project = self._project_for_entity(relationship.source_entity_id)
            target_project = self._project_for_entity(relationship.target_entity_id)
            if source_project and target_project and source_project != target_project:
                adjacency[source_project].add(target_project)
                adjacency[target_project].add(source_project)
        for impact in change_impact_results:
            affected_projects = [item.project_id for item in impact.affected_releases if item.project_id in project_ids]
            if len(affected_projects) < 2:
                continue
            ordered = sorted(_dedupe_preserve_order(affected_projects))
            for index, project_id in enumerate(ordered):
                for other in ordered[index + 1 :]:
                    adjacency[project_id].add(other)
                    adjacency[other].add(project_id)
        for context in contexts:
            project_id = context.project.project_id
            for dependency in context.dependency_projects:
                if dependency in project_ids:
                    adjacency[project_id].add(dependency)
                    adjacency[dependency].add(project_id)
        return self._connected_components(adjacency, project_ids)

    def _release_relationships(self) -> list[ArchitectureRelationshipRecord]:
        return [
            relationship
            for relationship in self.project_contract_service.database.list_architecture_relationships()
            if relationship.relationship_type == "RELEASES_WITH" and relationship.status == "approved"
        ]

    def _project_for_entity(self, entity_id: str) -> str | None:
        entity = self.project_contract_service.database.get_architecture_entity(entity_id)
        if entity is None:
            return None
        if entity.owning_project_or_domain and entity.owning_project_or_domain in self.settings.projects:
            return entity.owning_project_or_domain
        if entity.kind == "project":
            return entity.identity_key.removeprefix("project:") if entity.identity_key.startswith("project:") else entity.owning_project_or_domain
        return entity.owning_project_or_domain

    def _connected_components(self, adjacency: dict[str, set[str]], project_ids: set[str]) -> list[list[str]]:
        remaining = set(project_ids)
        groups: list[list[str]] = []
        while remaining:
            start = min(remaining)
            remaining.remove(start)
            queue = deque([start])
            component = {start}
            while queue:
                project_id = queue.popleft()
                for other in sorted(adjacency.get(project_id, set())):
                    if other in remaining:
                        remaining.remove(other)
                        component.add(other)
                        queue.append(other)
            if len(component) > 1:
                groups.append(sorted(component))
        return sorted(groups, key=lambda item: (len(item), item))

    def _build_release_train(
        self,
        group: list[str],
        contexts: list[_ProgrammeProjectContext],
        change_impact_results: list[ChangeImpactResult],
    ) -> ReleaseTrainRecord | None:
        context_by_project = {context.project.project_id: context for context in contexts if context.project.project_id in group}
        if len(context_by_project) < 2:
            return None
        ordered_projects, cycle_records = self._release_order(group, context_by_project)
        participants = [self._participant_for_project(project_id, order=index + 1, context=context_by_project[project_id]) for index, project_id in enumerate(ordered_projects)]
        if not participants:
            return None
        required_versions = self._required_versions_for_projects(participants, context_by_project)
        compatibility_constraints = self._compatibility_constraints(participants, required_versions, cycle_records, change_impact_results)
        blocking_evidence, release_readiness, freshness, trust = self._release_readiness(
            participants,
            required_versions,
            compatibility_constraints,
            cycle_records,
            change_impact_results,
            context_by_project,
        )
        required_tests = self._required_tests(participants, context_by_project, change_impact_results)
        rollback_relationships = self._rollback_relationships(participants, context_by_project)
        semantic_fingerprint = _content_fingerprint(
            {
                "participants": [participant.project_id for participant in participants],
                "versions": [item.model_dump(mode="json") for item in required_versions],
                "order": ordered_projects,
                "constraints": [item.model_dump(mode="json") for item in compatibility_constraints],
            }
        )
        train = ReleaseTrainRecord(
            release_train_id=_deterministic_id(
                "release-train",
                {
                    "participants": [participant.project_id for participant in participants],
                    "objective": self._train_objective(participants, context_by_project),
                    "versions": [item.model_dump(mode="json") for item in required_versions],
                },
            ),
            objective=self._train_objective(participants, context_by_project),
            semantic_fingerprint=semantic_fingerprint,
            participating_projects=participants,
            required_versions=required_versions,
            dependency_order=ordered_projects,
            compatibility_constraints=compatibility_constraints,
            blocking_evidence=blocking_evidence,
            required_tests=required_tests,
            rollback_relationships=rollback_relationships,
            release_readiness=release_readiness,
            human_approval_state="required",
            freshness=freshness,
            trust=trust,
            evidence_refs=self._train_evidence_refs(participants, required_versions, compatibility_constraints, change_impact_results),
            provenance=self._train_provenance(participants, context_by_project),
        )
        train.train_fingerprint = _content_fingerprint(
            _stable_fingerprint_value(
            {
                "semantic_fingerprint": train.semantic_fingerprint,
                "dependency_order": train.dependency_order,
                "release_readiness": train.release_readiness,
                "blocking_evidence": [item.model_dump(mode="json") for item in train.blocking_evidence],
                "required_tests": [item.model_dump(mode="json") for item in train.required_tests],
                "rollback_relationships": [item.model_dump(mode="json") for item in train.rollback_relationships],
            }
            )
        )
        return train

    def _release_order(
        self,
        group: list[str],
        context_by_project: dict[str, _ProgrammeProjectContext],
    ) -> tuple[list[str], list[DependencyGraphCycleRecord]]:
        edges: dict[str, set[str]] = defaultdict(set)
        reverse_edges: dict[str, set[str]] = defaultdict(set)
        for project_id in group:
            for dependency in self.dependency_graph_service.project_dependencies(project_id, transitive=False):
                if dependency.target_project_id in group:
                    edges[dependency.target_project_id].add(project_id)
                    reverse_edges[project_id].add(dependency.target_project_id)
        in_degree = {project_id: len(reverse_edges.get(project_id, set())) for project_id in group}
        queue = deque(sorted([project_id for project_id, degree in in_degree.items() if degree == 0]))
        ordered: list[str] = []
        while queue:
            project_id = queue.popleft()
            ordered.append(project_id)
            for dependent in sorted(edges.get(project_id, set())):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        cycle_records: list[DependencyGraphCycleRecord] = []
        if len(ordered) != len(group):
            ordered = sorted(group)
            cycle_records.append(
                DependencyGraphCycleRecord(
                    cycle_id=_deterministic_id("release-train-cycle", {"group": group}),
                    node_ids=ordered,
                    project_ids=ordered,
                    freshness_state="unknown",
                    trust_state="unknown",
                    details={"reason": "dependency_order_cycle"},
                )
            )
        return ordered, cycle_records

    def _participant_for_project(
        self,
        project_id: str,
        *,
        order: int,
        context: _ProgrammeProjectContext,
    ) -> ReleaseTrainParticipant:
        contract = context.contract
        revision = contract.current_revision if contract is not None else None
        freshness = _project_contract_freshness(contract)
        health_freshness = _project_health_freshness(context.health)
        readiness = self._participant_readiness(context)
        evidence_refs = self._train_participant_evidence_refs(context)
        current_version = revision.content.version if revision is not None else None
        return ReleaseTrainParticipant(
            project_id=project_id,
            project_name=context.project.name,
            order=order,
            current_version=current_version,
            release_channel=revision.content.release_channel if revision is not None else None,
            release_process_reference=revision.content.release_process_reference if revision is not None else None,
            readiness=readiness,
            freshness=_combine_freshness([freshness, health_freshness]),
            trust=_combine_trust([_trust_from_freshness(freshness), _trust_from_freshness(health_freshness)]),
            evidence_refs=evidence_refs,
            provenance=self._participant_provenance(context),
        )

    def _participant_readiness(self, context: _ProgrammeProjectContext) -> ProgrammeReadinessState:
        contract = context.contract
        health = context.health
        if contract is None or contract.current_revision is None:
            return "WAITING_FOR_EVIDENCE"
        if contract.status != "approved":
            return "BLOCKED"
        if health is None:
            return "WAITING_FOR_EVIDENCE"
        if health.normalized_status == "blocked":
            return "BLOCKED"
        if health.normalized_status == "attention":
            return "PARTIAL"
        freshness = _project_health_freshness(health)
        if freshness in {"stale", "unknown", "unavailable"}:
            return "WAITING_FOR_EVIDENCE"
        if contract.current_revision.freshness_state in {"stale", "unknown"}:
            return "WAITING_FOR_EVIDENCE"
        return "READY"

    def _required_versions_for_projects(
        self,
        participants: list[ReleaseTrainParticipant],
        context_by_project: dict[str, _ProgrammeProjectContext],
    ) -> list[ReleaseTrainVersionRequirement]:
        requirements: list[ReleaseTrainVersionRequirement] = []
        for participant in participants:
            context = context_by_project[participant.project_id]
            contract = context.contract
            revision = contract.current_revision if contract is not None else None
            requirements.append(
                ReleaseTrainVersionRequirement(
                    requirement_id=_deterministic_id(
                        "release-train-version",
                        {
                            "project_id": participant.project_id,
                            "version": participant.current_version,
                            "release_process_reference": participant.release_process_reference,
                        },
                    ),
                    project_id=participant.project_id,
                    version=participant.current_version,
                    release_channel=participant.release_channel,
                    release_process_reference=participant.release_process_reference,
                    contract_id=contract.contract_id if contract is not None else None,
                    contract_revision_id=revision.revision_id if revision is not None else None,
                    freshness=participant.freshness,
                    trust=participant.trust,
                    details={"status": contract.status if contract is not None else "missing"},
                )
            )
        return requirements

    def _compatibility_constraints(
        self,
        participants: list[ReleaseTrainParticipant],
        required_versions: list[ReleaseTrainVersionRequirement],
        cycle_records: list[DependencyGraphCycleRecord],
        change_impact_results: list[ChangeImpactResult],
    ) -> list[ProgrammeCompatibilityConstraint]:
        constraints: list[ProgrammeCompatibilityConstraint] = []
        for participant in participants:
            if participant.release_process_reference:
                constraints.append(
                    ProgrammeCompatibilityConstraint(
                        constraint_id=_deterministic_id(
                            "release-train-constraint",
                            {"project_id": participant.project_id, "kind": "shared_release_process", "reference": participant.release_process_reference},
                        ),
                        constraint_kind="shared_release_process",
                        description=f"Participant uses release process {participant.release_process_reference}.",
                        source_project_id=participant.project_id,
                        required_value=participant.release_process_reference,
                        observed_value=participant.release_process_reference,
                        freshness=participant.freshness,
                        trust=participant.trust,
                    )
                )
            if participant.current_version:
                constraints.append(
                    ProgrammeCompatibilityConstraint(
                        constraint_id=_deterministic_id(
                            "release-train-constraint",
                            {"project_id": participant.project_id, "kind": "version_requirement", "version": participant.current_version},
                        ),
                        constraint_kind="version_requirement",
                        description=f"Participant version {participant.current_version}.",
                        source_project_id=participant.project_id,
                        required_value=participant.current_version,
                        observed_value=participant.current_version,
                        freshness=participant.freshness,
                        trust=participant.trust,
                    )
                )
        for cycle in cycle_records:
            constraints.append(
                ProgrammeCompatibilityConstraint(
                    constraint_id=_deterministic_id("release-train-constraint", {"cycle_id": cycle.cycle_id}),
                    constraint_kind="dependency_order",
                    description="A release-order cycle was detected.",
                    freshness=cycle.freshness_state,
                    trust=cycle.trust_state,
                    details={"cycle_id": cycle.cycle_id, "project_ids": cycle.project_ids},
                )
            )
        for impact in change_impact_results:
            for release in impact.affected_releases:
                constraints.append(
                    ProgrammeCompatibilityConstraint(
                        constraint_id=_deterministic_id(
                            "release-train-constraint",
                            {"analysis_id": impact.analysis_id, "project_id": release.project_id, "kind": "change_impact_constraint"},
                        ),
                        constraint_kind="change_impact_constraint",
                        description=release.declared_release_contract or impact.proposal.objective,
                        source_project_id=release.project_id,
                        required_value=release.version_constraint,
                        observed_value=release.current_version,
                        freshness=release.freshness_state,
                        trust=cast(ProgrammeTrustState, release.trust_state),
                        details={"analysis_id": impact.analysis_id, "reason_codes": list(release.reason_codes)},
                    )
                )
        return constraints

    def _release_readiness(
        self,
        participants: list[ReleaseTrainParticipant],
        required_versions: list[ReleaseTrainVersionRequirement],
        compatibility_constraints: list[ProgrammeCompatibilityConstraint],
        cycle_records: list[DependencyGraphCycleRecord],
        change_impact_results: list[ChangeImpactResult],
        context_by_project: dict[str, _ProgrammeProjectContext],
    ) -> tuple[list[ProgrammeBlocker], ProgrammeReleaseReadinessState, str, ProgrammeTrustState]:
        blockers: list[ProgrammeBlocker] = []
        freshness = _combine_freshness([participant.freshness for participant in participants] + [constraint.freshness for constraint in compatibility_constraints])
        trust = _combine_trust([participant.trust for participant in participants] + [constraint.trust for constraint in compatibility_constraints])
        for participant in participants:
            if participant.readiness == "BLOCKED":
                blockers.append(
                    ProgrammeBlocker(
                        blocker_id=_deterministic_id("release-train-blocker", {"project_id": participant.project_id, "reason": "participant_blocked"}),
                        reason_code="participant_blocked",
                        description=f"Participant {participant.project_id} is blocked.",
                        source_kind="release_train",
                        source_id=participant.project_id,
                        severity="critical",
                        evidence_refs=participant.evidence_refs,
                        freshness=participant.freshness,
                    trust=participant.trust,
                    )
                )
            elif participant.readiness == "WAITING_FOR_EVIDENCE":
                blockers.append(
                    ProgrammeBlocker(
                        blocker_id=_deterministic_id("release-train-blocker", {"project_id": participant.project_id, "reason": "participant_waiting"}),
                        reason_code="participant_waiting_for_evidence",
                        description=f"Participant {participant.project_id} is waiting for evidence.",
                        source_kind="release_train",
                        source_id=participant.project_id,
                        severity="warning",
                        evidence_refs=participant.evidence_refs,
                        freshness=participant.freshness,
                    trust=participant.trust,
                    )
                )
        for cycle in cycle_records:
            blockers.append(
                ProgrammeBlocker(
                    blocker_id=_deterministic_id("release-train-blocker", {"cycle_id": cycle.cycle_id}),
                    reason_code="dependency_cycle",
                    description="Release-order cycle detected.",
                    source_kind="dependency_graph",
                    source_id=cycle.cycle_id,
                    severity="critical",
                    freshness=cycle.freshness_state,
                    trust=cycle.trust_state,
                    details={"project_ids": cycle.project_ids},
                )
            )
        for impact in change_impact_results:
            if impact.unknown_findings:
                blockers.append(
                    ProgrammeBlocker(
                        blocker_id=_deterministic_id("release-train-blocker", {"analysis_id": impact.analysis_id, "reason": "unknown_change_impact"}),
                        reason_code="unknown_change_impact",
                        description="Change impact analysis contains unknown findings.",
                        source_kind="change_impact",
                        source_id=impact.analysis_id,
                        severity="warning" if impact.risk.risk_level != "CRITICAL" else "critical",
                        evidence_refs=self._change_impact_evidence_refs(impact),
                        freshness=impact.freshness_state,
                        trust=cast(ProgrammeTrustState, impact.trust_state),
                    )
                )
        if any(blocker.severity == "critical" for blocker in blockers):
            readiness: ProgrammeReleaseReadinessState = "BLOCKED"
        elif any(participant.readiness == "WAITING_FOR_EVIDENCE" for participant in participants):
            readiness = "WAITING_FOR_EVIDENCE"
        elif any(participant.readiness == "PARTIAL" for participant in participants) or any(blocker.severity == "warning" for blocker in blockers):
            readiness = "READY_WITH_WARNINGS"
        elif any(item.freshness in {"stale", "unknown", "unavailable"} for item in participants):
            readiness = "PARTIAL"
        else:
            readiness = "READY"
        return blockers, readiness, freshness, trust

    def _required_tests(
        self,
        participants: list[ReleaseTrainParticipant],
        context_by_project: dict[str, _ProgrammeProjectContext],
        change_impact_results: list[ChangeImpactResult],
    ) -> list[ProgrammeValidationReference]:
        references: list[ProgrammeValidationReference] = []
        for participant in participants:
            context = context_by_project[participant.project_id]
            contract = context.contract
            if contract is None or contract.current_revision is None:
                continue
            revision = contract.current_revision
            for command in revision.content.test_commands:
                references.append(
                    ProgrammeValidationReference(
                        validation_id=_deterministic_id(
                            "release-train-validation",
                            {"project_id": participant.project_id, "kind": "test_command", "reference": command},
                        ),
                        project_id=participant.project_id,
                        reference_kind="test_command",
                        reference=command,
                        description=f"Test command for {participant.project_name}.",
                        source_id=revision.revision_id,
                        freshness=participant.freshness,
                        trust=participant.trust,
                    )
                )
            for command in revision.content.build_commands:
                references.append(
                    ProgrammeValidationReference(
                        validation_id=_deterministic_id(
                            "release-train-validation",
                            {"project_id": participant.project_id, "kind": "build_command", "reference": command},
                        ),
                        project_id=participant.project_id,
                        reference_kind="build_command",
                        reference=command,
                        description=f"Build command for {participant.project_name}.",
                        source_id=revision.revision_id,
                        freshness=participant.freshness,
                        trust=participant.trust,
                    )
                )
            for root in revision.content.documentation_roots:
                references.append(
                    ProgrammeValidationReference(
                        validation_id=_deterministic_id(
                            "release-train-validation",
                            {"project_id": participant.project_id, "kind": "documentation_root", "reference": root},
                        ),
                        project_id=participant.project_id,
                        reference_kind="documentation_root",
                        reference=root,
                        description=f"Documentation root for {participant.project_name}.",
                        source_id=revision.revision_id,
                        freshness=participant.freshness,
                        trust=participant.trust,
                    )
                )
            if revision.content.release_process_reference:
                references.append(
                    ProgrammeValidationReference(
                        validation_id=_deterministic_id(
                            "release-train-validation",
                            {"project_id": participant.project_id, "kind": "release_process_reference", "reference": revision.content.release_process_reference},
                        ),
                        project_id=participant.project_id,
                        reference_kind="release_process_reference",
                        reference=revision.content.release_process_reference,
                        description=f"Release process reference for {participant.project_name}.",
                        source_id=revision.revision_id,
                        freshness=participant.freshness,
                        trust=participant.trust,
                    )
                )
        for impact in change_impact_results:
            for validation in impact.validation_references:
                if validation.reference_kind not in {"test_command", "build_command", "documentation_root", "release_process_reference"}:
                    continue
                references.append(
                    ProgrammeValidationReference(
                        validation_id=_deterministic_id(
                            "release-train-validation",
                            {"project_id": validation.project_id, "analysis_id": impact.analysis_id, "reference": validation.reference},
                        ),
                        project_id=validation.project_id,
                        reference_kind=validation.reference_kind,
                        reference=validation.reference,
                        description=validation.description,
                        source_id=validation.source_contract_revision_id or validation.validation_id,
                        freshness=validation.freshness_state,
                        trust=cast(ProgrammeTrustState, validation.trust_state),
                        details={"analysis_id": impact.analysis_id},
                    )
                )
        deduped: dict[tuple[str, str, str], ProgrammeValidationReference] = {}
        for reference in references:
            key = (reference.project_id, reference.reference_kind, reference.reference)
            deduped[key] = reference
        return sorted(deduped.values(), key=lambda item: (item.project_id, item.reference_kind, item.reference))

    def _rollback_relationships(
        self,
        participants: list[ReleaseTrainParticipant],
        context_by_project: dict[str, _ProgrammeProjectContext],
    ) -> list[ProgrammeRollbackRelationship]:
        if len(participants) < 2:
            return []
        if len({participant.release_process_reference for participant in participants if participant.release_process_reference}) == 1:
            reference = next(participant.release_process_reference for participant in participants if participant.release_process_reference)
            if reference is not None:
                return [
                    ProgrammeRollbackRelationship(
                        rollback_relationship_id=_deterministic_id("release-train-rollback", {"reference": reference, "participants": [participant.project_id for participant in participants]}),
                        relationship_kind="must_rollback_together",
                        description=f"Projects coordinated by {reference} should rollback together if necessary.",
                        source_project_id=participants[0].project_id,
                        target_project_id=participants[-1].project_id,
                        freshness="fresh",
                        trust="trusted_with_warning",
                    )
                ]
        return []

    def _train_objective(self, participants: list[ReleaseTrainParticipant], context_by_project: dict[str, _ProgrammeProjectContext]) -> str:
        project_names = [context_by_project[participant.project_id].project.name for participant in participants]
        if len(project_names) == 2:
            return f"Coordinate releases for {project_names[0]} and {project_names[1]}."
        return f"Coordinate releases for {', '.join(project_names[:-1])} and {project_names[-1]}."

    def _train_evidence_refs(
        self,
        participants: list[ReleaseTrainParticipant],
        required_versions: list[ReleaseTrainVersionRequirement],
        compatibility_constraints: list[ProgrammeCompatibilityConstraint],
        change_impact_results: list[ChangeImpactResult],
    ) -> list[ProgrammeEvidenceReference]:
        refs: list[ProgrammeEvidenceReference] = []
        for participant in participants:
            refs.extend(participant.evidence_refs)
        refs.extend(
            ProgrammeEvidenceReference(
                evidence_kind="release_train_version",
                evidence_id=item.requirement_id,
                description=f"Version requirement for {item.project_id}.",
                freshness=item.freshness,
                details={"version": item.version},
            )
            for item in required_versions
        )
        refs.extend(
            ProgrammeEvidenceReference(
                evidence_kind="compatibility_constraint",
                evidence_id=item.constraint_id,
                description=item.description,
                freshness=item.freshness,
                details={"constraint_kind": item.constraint_kind},
            )
            for item in compatibility_constraints
        )
        for impact in change_impact_results:
            refs.extend(self._change_impact_evidence_refs(impact))
        deduped: dict[tuple[str, str], ProgrammeEvidenceReference] = {}
        for ref in refs:
            key = (ref.evidence_kind, ref.evidence_id or ref.description)
            deduped[key] = ref
        return sorted(deduped.values(), key=lambda item: (item.evidence_kind, item.evidence_id or "", item.description))

    def _train_provenance(
        self,
        participants: list[ReleaseTrainParticipant],
        context_by_project: dict[str, _ProgrammeProjectContext],
    ) -> ProgrammeProvenanceRecord:
        first = participants[0]
        context = context_by_project[first.project_id]
        details = {
            "participants": [participant.project_id for participant in participants],
            "train": "release",
        }
        return ProgrammeProvenanceRecord(
            source_project_id=first.project_id,
            repository=str(context.project.root),
            canonical_gaia_source="gaia",
            source_document="programme_release_train",
            evidence_reference="release_train",
            details=details,
        )

    def _change_impact_evidence_refs(self, impact: ChangeImpactResult) -> list[ProgrammeEvidenceReference]:
        refs = [
            ProgrammeEvidenceReference(
                evidence_kind="change_impact",
                evidence_id=impact.analysis_id,
                description=impact.proposal.title,
                freshness=impact.freshness_state,
                details={"risk": impact.risk.risk_level, "proposal_id": impact.proposal_id},
            )
        ]
        for validation in impact.validation_references:
            refs.append(
                ProgrammeEvidenceReference(
                    evidence_kind=f"validation:{validation.reference_kind}",
                    evidence_id=validation.validation_id,
                    description=validation.description,
                    freshness=validation.freshness_state,
                    details={"reference": validation.reference},
                )
            )
        return refs

    def _participant_provenance(self, context: _ProgrammeProjectContext) -> ProgrammeProvenanceRecord:
        return ProgrammeProvenanceRecord(
            source_project_id=context.project.project_id,
            repository=str(context.project.root),
            canonical_gaia_source="gaia",
            source_document="project_contract",
            evidence_reference=context.contract.current_revision_id if context.contract is not None else None,
            details={"project_name": context.project.name},
        )

    def _train_participant_evidence_refs(self, context: _ProgrammeProjectContext) -> list[ProgrammeEvidenceReference]:
        refs: list[ProgrammeEvidenceReference] = []
        if context.contract is not None and context.contract.current_revision is not None:
            revision = context.contract.current_revision
            refs.append(
                ProgrammeEvidenceReference(
                    evidence_kind="project_contract",
                    evidence_id=revision.revision_id,
                    description=f"Approved contract for {context.project.project_id}.",
                    freshness=revision.freshness_state,
                    details={"version": revision.content.version, "release_process_reference": revision.content.release_process_reference},
                )
            )
        if context.health is not None:
            refs.append(
                ProgrammeEvidenceReference(
                    evidence_kind="project_health_snapshot",
                    evidence_id=_stable_project_health_identity(context.project.project_id, context.health),
                    description=f"Latest health snapshot for {context.project.project_id}.",
                    freshness=_project_health_freshness(context.health),
                    details={"normalized_status": context.health.normalized_status},
                )
            )
            refs.append(
                ProgrammeEvidenceReference(
                    evidence_kind="project_health_condition",
                    evidence_id=f"{context.project.project_id}:{context.health.normalized_status}",
                    description=f"Project health status is {context.health.normalized_status}.",
                    freshness=_project_health_freshness(context.health),
                    details={"blocking_conditions": list(context.health.blocking_conditions), "attention_conditions": list(context.health.attention_conditions)},
                )
            )
        return refs

    def _portfolio_payload(self, portfolio: ReleaseTrainPortfolio) -> dict[str, Any]:
        return {
            "release_trains": [train.model_dump(mode="json") for train in portfolio.release_trains],
            "counts_by_readiness": portfolio.counts_by_readiness,
        }


class ProgrammeIntelligenceService:
    def __init__(
        self,
        settings: Settings,
        project_contract_service: ProjectContractService,
        project_health_service: ProjectHealthService,
        recommendation_service: RecommendationService,
        work_package_service: WorkPackageService,
        dependency_graph_service: DependencyGraphService,
    ) -> None:
        self.roadmap_service = ProgrammeRoadmapService(
            settings,
            project_contract_service,
            project_health_service,
            recommendation_service,
            work_package_service,
            dependency_graph_service,
        )
        self.release_train_service = ReleaseTrainService(
            settings,
            project_contract_service,
            project_health_service,
            dependency_graph_service,
        )

    def programme_roadmap(self, *, change_impact_results: Iterable[ChangeImpactResult] | None = None) -> ProgrammeRoadmapPortfolio:
        return self.roadmap_service.roadmap_view(change_impact_results=change_impact_results)

    def release_trains(self, *, change_impact_results: Iterable[ChangeImpactResult] | None = None) -> ReleaseTrainPortfolio:
        return self.release_train_service.release_trains(change_impact_results=change_impact_results)
