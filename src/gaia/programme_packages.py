from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field

from gaia.change_impact import ChangeImpactResult
from gaia.config import Settings
from gaia.db import Database
from gaia.dependency_graph import DependencyGraphService
from gaia.models import (
    WorkPackageApprovalState,
    WorkPackageGateState,
    WorkPackageRecord,
    WorkPackageRiskClassification,
    WorkPackageStalenessState,
    utc_now,
)
from gaia.programme_intelligence import (
    ProgrammeEvidenceReference,
    ProgrammeIntelligenceService,
    ReleaseTrainPortfolio,
    ReleaseTrainRecord,
)
from gaia.programme_registry import ProgrammeProvenanceRecord, ProjectContractService
from gaia.work_packages import WorkPackageService

ProgrammePackageState = Literal[
    "proposed",
    "under_review",
    "approved",
    "rejected",
    "superseded",
    "expired",
    "handed_off",
    "partially_completed",
    "completed",
    "failed",
    "rolled_back",
]
ProgrammePackageHumanApprovalState = Literal["required", "pending", "approved", "rejected", "unknown"]
ProgrammePackageSeverity = Literal["info", "low", "medium", "high", "critical"]


class ProgrammePackageWorkPackageReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    work_package_id: str
    revision_id: str | None = None
    revision_number: int = 0
    project_id: str
    title: str
    objective: str
    approval_state: WorkPackageApprovalState = "proposed"
    gate_state: WorkPackageGateState = "open"
    staleness_state: WorkPackageStalenessState = "fresh"
    risk_classification: WorkPackageRiskClassification = "unknown"
    freshness: str = "unknown"
    trust: str = "unknown"
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)


class ProgrammePackageRiskRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk_id: str
    description: str
    severity: ProgrammePackageSeverity = "medium"
    source_kind: str = "programme_package"
    source_id: str | None = None
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ProgrammePackageProjectAcceptanceRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: str
    work_package_ids: list[str] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)


class ProgrammePackageHumanApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    approval_state: ProgrammePackageHumanApprovalState = "required"
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    note: str | None = None
    evidence_refs: list[ProgrammeEvidenceReference] = Field(default_factory=list)


class ProgrammePackageRevisionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revision_id: str = Field(default_factory=lambda: str(uuid4()))
    package_id: str
    revision_number: int
    previous_revision_id: str | None = None
    change_reason: str = ""
    package_state_at_creation: ProgrammePackageState = "proposed"
    semantic_fingerprint: str = ""
    content_fingerprint: str = ""
    package_fingerprint: str = ""
    created_timestamp: datetime = Field(default_factory=utc_now)
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    normalized_payload: dict[str, Any] = Field(default_factory=dict)


class ProgrammePackageRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    programme_package_id: str
    objective: str
    projects_involved: list[str] = Field(default_factory=list)
    project_work_packages: list[ProgrammePackageWorkPackageReference] = Field(default_factory=list)
    dependency_order: list[str] = Field(default_factory=list)
    change_impact_evidence: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    architecture_references: list[ProgrammeEvidenceReference] = Field(default_factory=list)
    risks: list[ProgrammePackageRiskRecord] = Field(default_factory=list)
    global_acceptance_criteria: list[str] = Field(default_factory=list)
    per_project_acceptance_criteria: list[ProgrammePackageProjectAcceptanceRecord] = Field(default_factory=list)
    rollback_coordination: list[str] = Field(default_factory=list)
    release_sequence: list[str] = Field(default_factory=list)
    human_approval: ProgrammePackageHumanApprovalRecord = Field(default_factory=ProgrammePackageHumanApprovalRecord)
    revision_history: list[ProgrammePackageRevisionRecord] = Field(default_factory=list)
    provenance: ProgrammeProvenanceRecord = Field(default_factory=ProgrammeProvenanceRecord)
    package_state: ProgrammePackageState = "proposed"
    semantic_fingerprint: str = ""
    content_fingerprint: str = ""
    package_fingerprint: str = ""
    current_revision_id: str | None = None
    current_revision_number: int = 1
    created_timestamp: datetime = Field(default_factory=utc_now)
    updated_timestamp: datetime = Field(default_factory=utc_now)
    normalized_payload: dict[str, Any] = Field(default_factory=dict)


class ProgrammePackagePortfolio(BaseModel):
    model_config = ConfigDict(extra="ignore")

    generated_at: datetime = Field(default_factory=utc_now)
    programme_packages: list[ProgrammePackageRecord] = Field(default_factory=list)
    counts_by_state: dict[str, int] = Field(default_factory=dict)
    package_fingerprint: str = ""


@dataclass(slots=True)
class _BuiltPackage:
    package: ProgrammePackageRecord
    revision: ProgrammePackageRevisionRecord


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _content_fingerprint(value: Any) -> str:
    return _sha256_text(_json_dumps(value))


def _stable_fingerprint_value(value: Any) -> Any:
    volatile_keys = {"captured_at", "created_timestamp", "updated_timestamp", "audit_event_id", "event_id"}
    if isinstance(value, dict):
        return {key: _stable_fingerprint_value(item) for key, item in value.items() if key not in volatile_keys}
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


def _package_state_from_work_packages(packages: list[WorkPackageRecord]) -> ProgrammePackageState:
    if not packages:
        return "proposed"
    states = [package.approval_state for package in packages]
    if all(state == "rolled_back" for state in states):
        return "rolled_back"
    if any(state == "rolled_back" for state in states):
        return "partially_completed"
    if all(state == "failed" for state in states):
        return "failed"
    if any(state == "failed" for state in states):
        return "partially_completed"
    if all(state == "completed" for state in states):
        return "completed"
    if any(state == "completed" for state in states):
        return "partially_completed"
    if all(state == "handed_off" for state in states):
        return "handed_off"
    if any(state == "handed_off" for state in states):
        return "approved"
    if any(state == "under_review" for state in states):
        return "under_review"
    if any(state == "approved" for state in states):
        return "approved"
    if all(state == "rejected" for state in states):
        return "rejected"
    if all(state == "expired" for state in states):
        return "expired"
    return "proposed"


def _human_approval_state_from_package_state(package_state: ProgrammePackageState) -> ProgrammePackageHumanApprovalState:
    if package_state in {"approved", "handed_off", "completed"}:
        return "pending"
    if package_state in {"failed", "rolled_back", "expired", "rejected"}:
        return "required"
    return "required"


class ProgrammePackageService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        project_contract_service: ProjectContractService,
        work_package_service: WorkPackageService,
        dependency_graph_service: DependencyGraphService,
        programme_intelligence_service: ProgrammeIntelligenceService,
    ) -> None:
        self.settings = settings
        self.database = database
        self.project_contract_service = project_contract_service
        self.work_package_service = work_package_service
        self.dependency_graph_service = dependency_graph_service
        self.programme_intelligence_service = programme_intelligence_service

    def programme_packages(self, *, change_impact_results: Iterable[ChangeImpactResult] | None = None) -> ProgrammePackagePortfolio:
        release_portfolio = self.programme_intelligence_service.release_trains(change_impact_results=change_impact_results)
        work_packages = self._reviewable_work_packages()
        candidates = self._build_candidates(release_portfolio, work_packages, list(change_impact_results or []))
        persisted = [self._persist_candidate(candidate) for candidate in candidates]
        persisted.sort(key=lambda item: (item.package_state, item.package_fingerprint, item.programme_package_id))
        portfolio = ProgrammePackagePortfolio(
            generated_at=utc_now(),
            programme_packages=persisted,
            counts_by_state=dict(sorted(Counter(package.package_state for package in persisted).items())),
        )
        portfolio.package_fingerprint = _content_fingerprint(_stable_fingerprint_value(self._portfolio_payload(portfolio)))
        return portfolio

    def programme_package(self, package_id: str) -> ProgrammePackageRecord | None:
        package = self.database.get_programme_package(package_id)
        if package is None:
            return None
        return self._attach_revision_history(package)

    def programme_package_revisions(self, package_id: str) -> list[ProgrammePackageRevisionRecord]:
        return self.database.list_programme_package_revisions(package_id)

    def _reviewable_work_packages(self) -> list[WorkPackageRecord]:
        reviewable_states = {"proposed", "under_review", "approved", "handed_off"}
        packages = [package for package in self.work_package_service.list_work_packages() if package.approval_state in reviewable_states]
        return sorted(packages, key=lambda item: (item.project_id, item.current_revision_number, item.work_package_id))

    def _build_candidates(
        self,
        release_portfolio: ReleaseTrainPortfolio,
        work_packages: list[WorkPackageRecord],
        change_impact_results: list[ChangeImpactResult],
    ) -> list[_BuiltPackage]:
        by_project: dict[str, list[WorkPackageRecord]] = {}
        for package in work_packages:
            by_project.setdefault(package.project_id, []).append(package)

        candidates: list[_BuiltPackage] = []
        for train in release_portfolio.release_trains:
            package_work_packages = self._packages_for_train(train, by_project)
            if len({item.project_id for item in package_work_packages}) < 2 or len(package_work_packages) < 2:
                continue
            candidate = self._build_package(train, package_work_packages, change_impact_results)
            candidates.append(candidate)
        return sorted(candidates, key=lambda item: (item.package.package_state, item.package.package_fingerprint, item.package.programme_package_id))

    def _packages_for_train(
        self,
        train: ReleaseTrainRecord,
        by_project: dict[str, list[WorkPackageRecord]],
    ) -> list[WorkPackageRecord]:
        ordered: list[WorkPackageRecord] = []
        for project_id in train.dependency_order or [participant.project_id for participant in train.participating_projects]:
            ordered.extend(by_project.get(project_id, []))
        return ordered

    def _build_package(
        self,
        train: ReleaseTrainRecord,
        work_packages: list[WorkPackageRecord],
        change_impact_results: list[ChangeImpactResult],
    ) -> _BuiltPackage:
        projects_involved = _dedupe_preserve_order([package.project_id for package in work_packages] or [participant.project_id for participant in train.participating_projects])
        project_work_package_refs = [self._work_package_reference(package) for package in work_packages]
        package_state = _package_state_from_work_packages(work_packages)
        human_approval = ProgrammePackageHumanApprovalRecord(
            approval_state=_human_approval_state_from_package_state(package_state),
            evidence_refs=self._package_human_approval_evidence_refs(train),
        )
        change_impact_evidence = self._change_impact_evidence_refs(train, change_impact_results)
        architecture_refs = self._architecture_references(projects_involved)
        risks = self._package_risks(train, work_packages, change_impact_results)
        global_acceptance = self._global_acceptance_criteria(train, work_packages, change_impact_results)
        per_project_acceptance = self._per_project_acceptance_criteria(work_packages)
        rollback_coordination = self._rollback_coordination(train, work_packages)
        release_sequence = train.dependency_order or projects_involved
        semantic_fingerprint = _content_fingerprint(
            {
                "objective": train.objective,
                "projects_involved": projects_involved,
                "work_package_ids": [package.work_package_id for package in work_packages],
                "release_sequence": release_sequence,
                "train_fingerprint": train.train_fingerprint,
            }
        )
        package_id = _deterministic_id(
            "programme-package",
            {
                "objective": train.objective,
                "projects_involved": projects_involved,
                "work_package_ids": [package.work_package_id for package in work_packages],
                "train_fingerprint": train.train_fingerprint,
            },
        )
        provenance = ProgrammeProvenanceRecord(
            source_project_id=projects_involved[0] if projects_involved else train.participating_projects[0].project_id if train.participating_projects else None,
            repository=str(self.settings.projects[projects_involved[0]].root) if projects_involved and projects_involved[0] in self.settings.projects else None,
            canonical_gaia_source="gaia",
            source_document="programme_package",
            evidence_reference=package_id,
            details={
                "release_train_id": train.release_train_id,
                "release_train_fingerprint": train.train_fingerprint,
                "projects_involved": projects_involved,
                "work_package_ids": [package.work_package_id for package in work_packages],
            },
        )
        package = ProgrammePackageRecord(
            programme_package_id=package_id,
            objective=train.objective,
            projects_involved=projects_involved,
            project_work_packages=project_work_package_refs,
            dependency_order=release_sequence,
            change_impact_evidence=change_impact_evidence,
            architecture_references=architecture_refs,
            risks=risks,
            global_acceptance_criteria=global_acceptance,
            per_project_acceptance_criteria=per_project_acceptance,
            rollback_coordination=rollback_coordination,
            release_sequence=release_sequence,
            human_approval=human_approval,
            provenance=provenance,
            package_state=package_state,
            semantic_fingerprint=semantic_fingerprint,
        )
        package.content_fingerprint = _content_fingerprint(
            _stable_fingerprint_value(
                package.model_dump(mode="json", exclude={"content_fingerprint", "package_fingerprint", "revision_history"})
            )
        )
        package.package_fingerprint = _content_fingerprint({"semantic": package.semantic_fingerprint, "content": package.content_fingerprint})
        revision = ProgrammePackageRevisionRecord(
            revision_id=_deterministic_id(
                "programme-package-revision",
                {"package_id": package.programme_package_id, "revision_number": 1, "semantic": package.semantic_fingerprint, "content": package.content_fingerprint},
            ),
            package_id=package.programme_package_id,
            revision_number=1,
            change_reason="initial programme package derivation",
            package_state_at_creation=package.package_state,
            semantic_fingerprint=package.semantic_fingerprint,
            content_fingerprint=package.content_fingerprint,
            package_fingerprint=package.package_fingerprint,
            provenance=provenance,
        )
        package.current_revision_id = revision.revision_id
        package.current_revision_number = 1
        package.revision_history = [revision]
        package.normalized_payload = package.model_dump(mode="json")
        revision.normalized_payload = revision.model_dump(mode="json")
        return _BuiltPackage(package=package, revision=revision)

    def _work_package_reference(self, package: WorkPackageRecord) -> ProgrammePackageWorkPackageReference:
        evidence_refs = [
            ProgrammeEvidenceReference(
                evidence_kind="work_package_revision",
                evidence_id=package.current_revision_id,
                description=f"Current revision for work package {package.work_package_id}.",
                freshness=package.staleness_state,
                details={"revision_number": package.current_revision_number, "approval_state": package.approval_state},
            )
        ]
        if package.provenance_reference:
            evidence_refs.append(
                ProgrammeEvidenceReference(
                    evidence_kind="work_package_provenance",
                    evidence_id=package.provenance_reference,
                    description=f"Provenance reference for {package.work_package_id}.",
                    freshness=package.staleness_state,
                )
            )
        provenance = ProgrammeProvenanceRecord(
            source_project_id=package.project_id,
            repository=self._project_repository(package.project_id),
            canonical_gaia_source="gaia",
            source_document="work_package",
            evidence_reference=package.work_package_id,
            details={"title": package.title, "objective": package.objective},
        )
        return ProgrammePackageWorkPackageReference(
            work_package_id=package.work_package_id,
            revision_id=package.current_revision_id,
            revision_number=package.current_revision_number,
            project_id=package.project_id,
            title=package.title,
            objective=package.objective,
            approval_state=package.approval_state,
            gate_state=package.gate_state,
            staleness_state=package.staleness_state,
            risk_classification=package.risk_classification,
            freshness=package.staleness_state,
            trust="trusted" if package.staleness_state == "fresh" else "unknown",
            evidence_refs=evidence_refs,
            provenance=provenance,
        )

    def _project_repository(self, project_id: str) -> str | None:
        project = self.settings.projects.get(project_id)
        return str(project.root) if project is not None else None

    def _architecture_references(self, projects_involved: list[str]) -> list[ProgrammeEvidenceReference]:
        refs: list[ProgrammeEvidenceReference] = []
        for project_id in projects_involved:
            contract = self.project_contract_service.current_approved_contract(project_id)
            if contract is None or contract.current_revision is None:
                continue
            revision = contract.current_revision
            references = list(revision.content.architecture_references)
            if not references and revision.content.release_process_reference:
                references = [revision.content.release_process_reference]
            for reference in references:
                if not reference:
                    continue
                refs.append(
                    ProgrammeEvidenceReference(
                        evidence_kind="architecture_reference",
                        evidence_id=_deterministic_id(
                            "programme-package-architecture-reference",
                            {"project_id": project_id, "reference": reference, "revision_id": revision.revision_id},
                        ),
                        description=f"Architecture reference for {project_id}.",
                        freshness=revision.freshness_state,
                        details={"reference": reference, "project_id": project_id},
                    )
                )
        return sorted(refs, key=lambda item: (item.evidence_kind, item.evidence_id or "", item.description))

    def _change_impact_evidence_refs(
        self,
        train: ReleaseTrainRecord,
        change_impact_results: list[ChangeImpactResult],
    ) -> list[ProgrammeEvidenceReference]:
        refs: list[ProgrammeEvidenceReference] = []
        impacted_projects = set(train.dependency_order or [participant.project_id for participant in train.participating_projects])
        for impact in change_impact_results:
            if not impacted_projects.intersection({item.project_id for item in impact.affected_projects}):
                continue
            refs.append(
                ProgrammeEvidenceReference(
                    evidence_kind="change_impact",
                    evidence_id=impact.analysis_id,
                    description=impact.proposal.title,
                    freshness=impact.freshness_state,
                    details={"risk": impact.risk.risk_level, "affected_projects": [item.project_id for item in impact.affected_projects]},
                )
            )
        return sorted(refs, key=lambda item: (item.evidence_kind, item.evidence_id or "", item.description))

    def _package_human_approval_evidence_refs(self, train: ReleaseTrainRecord) -> list[ProgrammeEvidenceReference]:
        return [
            ProgrammeEvidenceReference(
                evidence_kind="release_train",
                evidence_id=train.release_train_id,
                description=f"Release train {train.release_train_id} underpins this programme package.",
                freshness=train.freshness,
                details={"readiness": train.release_readiness, "projects": train.participating_projects},
            )
        ]

    def _package_risks(
        self,
        train: ReleaseTrainRecord,
        work_packages: list[WorkPackageRecord],
        change_impact_results: list[ChangeImpactResult],
    ) -> list[ProgrammePackageRiskRecord]:
        risks: list[ProgrammePackageRiskRecord] = []
        for blocker in train.blocking_evidence:
            risks.append(
                ProgrammePackageRiskRecord(
                    risk_id=_deterministic_id("programme-package-risk", {"train": train.release_train_id, "blocker": blocker.blocker_id}),
                    description=blocker.description,
                    severity=self._severity_from_blocker(blocker.severity),
                    source_kind=blocker.source_kind,
                    source_id=blocker.source_id,
                    evidence_refs=blocker.evidence_refs,
                    details={"reason_code": blocker.reason_code, "freshness": blocker.freshness, "trust": blocker.trust},
                )
            )
        for package in work_packages:
            if package.approval_state in {"approved", "handed_off"}:
                continue
            risks.append(
                ProgrammePackageRiskRecord(
                    risk_id=_deterministic_id("programme-package-risk", {"package_id": package.work_package_id, "state": package.approval_state}),
                    description=f"Work package {package.work_package_id} is {package.approval_state}.",
                    severity="high" if package.approval_state in {"under_review", "proposed"} else "critical",
                    source_kind="work_package",
                    source_id=package.work_package_id,
                    evidence_refs=self._work_package_reference(package).evidence_refs,
                    details={"project_id": package.project_id, "approval_state": package.approval_state},
                )
            )
        for impact in change_impact_results:
            if impact.unknown_findings:
                risks.append(
                    ProgrammePackageRiskRecord(
                        risk_id=_deterministic_id("programme-package-risk", {"analysis_id": impact.analysis_id, "kind": "unknown_change_impact"}),
                        description="Change impact analysis contains unknown findings.",
                        severity="medium" if impact.risk.risk_level != "CRITICAL" else "critical",
                        source_kind="change_impact",
                        source_id=impact.analysis_id,
                        evidence_refs=self._change_impact_evidence_refs(train, [impact]),
                        details={"risk": impact.risk.risk_level},
                    )
                )
        return sorted(risks, key=lambda item: (item.severity, item.source_kind, item.source_id or "", item.risk_id))

    def _severity_from_blocker(self, severity: str) -> ProgrammePackageSeverity:
        if severity == "critical":
            return "critical"
        if severity == "warning":
            return "high"
        if severity == "info":
            return "low"
        return "medium"

    def _global_acceptance_criteria(
        self,
        train: ReleaseTrainRecord,
        work_packages: list[WorkPackageRecord],
        change_impact_results: list[ChangeImpactResult],
    ) -> list[str]:
        criteria = [
            "All participating work packages must be human-reviewed before handoff.",
            "The release sequence must respect the recorded dependency order.",
            "Rollback coordination must be recorded for each participating project.",
        ]
        if change_impact_results:
            criteria.append("Change-impact evidence must remain visible during package review.")
        if any(package.approval_state != "approved" for package in work_packages):
            criteria.append("Pending work packages must be approved before the programme package is handed off.")
        if train.required_tests:
            criteria.append("Required validation references must remain attached to the package.")
        return criteria

    def _per_project_acceptance_criteria(self, work_packages: list[WorkPackageRecord]) -> list[ProgrammePackageProjectAcceptanceRecord]:
        grouped: dict[str, list[WorkPackageRecord]] = {}
        for package in work_packages:
            grouped.setdefault(package.project_id, []).append(package)
        records: list[ProgrammePackageProjectAcceptanceRecord] = []
        for project_id in sorted(grouped):
            packages = sorted(grouped[project_id], key=lambda item: (item.current_revision_number, item.work_package_id))
            criteria = []
            for package in packages:
                criteria.extend(
                    [
                        f"Review work package {package.work_package_id} revision {package.current_revision_number}.",
                        f"Confirm the package objective for {package.title}.",
                    ]
                )
            records.append(
                ProgrammePackageProjectAcceptanceRecord(
                    project_id=project_id,
                    work_package_ids=[package.work_package_id for package in packages],
                    criteria=_dedupe_preserve_order(criteria),
                    evidence_refs=[self._work_package_reference(package).evidence_refs[0] for package in packages if self._work_package_reference(package).evidence_refs],
                )
            )
        return records

    def _rollback_coordination(self, train: ReleaseTrainRecord, work_packages: list[WorkPackageRecord]) -> list[str]:
        rollback_steps: list[str] = []
        for relationship in train.rollback_relationships:
            rollback_steps.append(relationship.description)
        for package in work_packages:
            rollback_steps.append(f"Return {package.work_package_id} to the last approved revision if execution is rolled back.")
        return _dedupe_preserve_order(rollback_steps)

    def _persist_candidate(self, candidate: _BuiltPackage) -> ProgrammePackageRecord:
        existing = self.database.get_programme_package_by_semantic(candidate.package.semantic_fingerprint)
        if existing is None:
            self.database.insert_programme_package(candidate.package)
            self.database.insert_programme_package_revision(candidate.revision)
            return self._attach_revision_history(candidate.package)

        if existing.content_fingerprint == candidate.package.content_fingerprint:
            return self._attach_revision_history(existing)

        package = existing.model_copy(deep=True)
        package.objective = candidate.package.objective
        package.projects_involved = candidate.package.projects_involved
        package.project_work_packages = candidate.package.project_work_packages
        package.dependency_order = candidate.package.dependency_order
        package.change_impact_evidence = candidate.package.change_impact_evidence
        package.architecture_references = candidate.package.architecture_references
        package.risks = candidate.package.risks
        package.global_acceptance_criteria = candidate.package.global_acceptance_criteria
        package.per_project_acceptance_criteria = candidate.package.per_project_acceptance_criteria
        package.rollback_coordination = candidate.package.rollback_coordination
        package.release_sequence = candidate.package.release_sequence
        package.human_approval = candidate.package.human_approval
        package.package_state = candidate.package.package_state
        package.semantic_fingerprint = candidate.package.semantic_fingerprint
        package.content_fingerprint = candidate.package.content_fingerprint
        package.package_fingerprint = candidate.package.package_fingerprint
        package.current_revision_id = candidate.revision.revision_id
        package.current_revision_number = existing.current_revision_number + 1
        package.updated_timestamp = utc_now()
        package.provenance = candidate.package.provenance
        package.normalized_payload = {}

        revision = candidate.revision.model_copy(deep=True)
        revision.revision_id = _deterministic_id(
            "programme-package-revision",
            {
                "package_id": package.programme_package_id,
                "revision_number": package.current_revision_number,
                "semantic": package.semantic_fingerprint,
                "content": package.content_fingerprint,
            },
        )
        revision.package_id = package.programme_package_id
        revision.revision_number = package.current_revision_number
        revision.previous_revision_id = existing.current_revision_id
        revision.normalized_payload = revision.model_dump(mode="json")

        self.database.insert_programme_package_revision(revision)
        package.revision_history = self.database.list_programme_package_revisions(package.programme_package_id)
        package.normalized_payload = package.model_dump(mode="json")
        self.database.insert_programme_package(package)
        return self._attach_revision_history(package)

    def _attach_revision_history(self, package: ProgrammePackageRecord) -> ProgrammePackageRecord:
        history = self.database.list_programme_package_revisions(package.programme_package_id)
        package = package.model_copy(deep=True)
        package.revision_history = sorted(history, key=lambda item: item.revision_number)
        return package

    def _portfolio_payload(self, portfolio: ProgrammePackagePortfolio) -> dict[str, Any]:
        return {
            "programme_packages": [package.model_dump(mode="json") for package in portfolio.programme_packages],
            "counts_by_state": portfolio.counts_by_state,
        }
