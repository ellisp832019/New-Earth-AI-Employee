from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from gaia.config import Settings
from gaia.db import Database
from gaia.models import (
    CapabilityDescriptor,
    ProjectChangeFinding,
    ProjectChangePortfolio,
    ProjectHealthPortfolio,
    ProjectHealthPortfolioEntry,
    ProjectHealthSnapshot,
    ProjectRecommendation,
    ProjectRecommendationPortfolio,
    WorkPackageApprovalDecisionRecord,
    WorkPackageHandoffRecord,
    WorkPackageOutcome,
    WorkPackageOutcomeRecord,
    WorkPackageRecord,
    WorkPackageRevisionRecord,
)
from gaia.service import ProjectService

ProjectOfficerAuthorityLevel = Literal["read_only", "gaia_local_state", "manual_handoff_only", "unsupported"]


class ProjectOfficerApiError(BaseModel):
    error_code: str
    message: str
    resource_type: str | None = None
    resource_id: str | None = None
    authority_level: ProjectOfficerAuthorityLevel | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProjectOfficerLifecycleRequest(BaseModel):
    revision_number: int = Field(ge=1)
    actor: str = "manual"
    human_note: str | None = None


class ProjectOfficerHandoffRequest(BaseModel):
    revision_number: int = Field(ge=1)
    approved_by: str = "manual"
    next_manual_action: str = "Copy the approved Codex prompt into Codex."
    rollback_reference: str = "Return to the recorded baseline commit or last approved revision."


class ProjectOfficerOutcomeRequest(BaseModel):
    revision_number: int = Field(ge=1)
    outcome: WorkPackageOutcome
    actor: str = "manual"
    note: str | None = None


class ProjectOfficerCapabilityCatalog(BaseModel):
    api_version: str = "0.10.0"
    contract_version: str = "gaia-v3"
    capability_version: str = "0.10.0"
    capabilities: list[str] = Field(default_factory=list)
    capability_catalog: list[CapabilityDescriptor] = Field(default_factory=list)
    degraded_features: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class ProjectOfficerService:
    project_service: ProjectService

    @property
    def database(self) -> Database:
        return self.project_service.database

    @property
    def settings(self) -> Settings:
        return self.project_service.settings

    def capabilities(self) -> ProjectOfficerCapabilityCatalog:
        descriptors = [
            CapabilityDescriptor(
                capability_id="project_officer_portfolio",
                version="0.10.0",
                state="enabled",
                summary="Inspect the portfolio of project-health and planning evidence.",
                authority_level="read_only",
            ),
            CapabilityDescriptor(
                capability_id="project_officer_project_health",
                version="0.10.0",
                state="enabled",
                summary="Inspect project-health snapshots and history.",
                authority_level="read_only",
            ),
            CapabilityDescriptor(
                capability_id="project_officer_change_intelligence",
                version="0.10.0",
                state="enabled",
                summary="Inspect change findings, comparisons and portfolio drift.",
                authority_level="read_only",
            ),
            CapabilityDescriptor(
                capability_id="project_officer_recommendations",
                version="0.10.0",
                state="enabled",
                summary="Inspect deterministic recommendations, score breakdowns and blockers.",
                authority_level="read_only",
            ),
            CapabilityDescriptor(
                capability_id="project_officer_work_packages",
                version="0.10.0",
                state="enabled",
                summary="Inspect work packages, revisions, approvals, handoffs and outcomes.",
                authority_level="read_only",
            ),
            CapabilityDescriptor(
                capability_id="project_officer_lifecycle_review",
                version="0.10.0",
                state="enabled",
                summary="Submit exact revisions for human review without executing work.",
                authority_level="gaia_local_state",
            ),
            CapabilityDescriptor(
                capability_id="project_officer_lifecycle_approval",
                version="0.10.0",
                state="enabled",
                summary="Approve or reject exact revisions as GAIA-local state changes.",
                authority_level="gaia_local_state",
            ),
            CapabilityDescriptor(
                capability_id="project_officer_lifecycle_handoff",
                version="0.10.0",
                state="enabled",
                summary="Record the exact handoff evidence for a manually approved revision.",
                authority_level="manual_handoff_only",
            ),
            CapabilityDescriptor(
                capability_id="project_officer_lifecycle_outcome",
                version="0.10.0",
                state="enabled",
                summary="Record a permitted human-reported work-package outcome.",
                authority_level="gaia_local_state",
            ),
            CapabilityDescriptor(
                capability_id="windows_project_officer_workspace",
                version="0.10.0",
                state="enabled",
                summary="Windows Control Centre workspace for B5 review and handoff flows.",
                authority_level="read_only",
            ),
            CapabilityDescriptor(
                capability_id="windows_programme_workspace",
                version="0.10.0",
                state="enabled",
                summary="Windows Control Centre workspace for C6 programme intelligence review.",
                authority_level="read_only",
            ),
            CapabilityDescriptor(
                capability_id="dashboard_read_only_compatibility",
                version="0.10.0",
                state="enabled",
                summary="Dashboard integration remains read-only and backward compatible.",
                authority_level="read_only",
            ),
        ]
        return ProjectOfficerCapabilityCatalog(
            capabilities=[descriptor.capability_id for descriptor in descriptors],
            capability_catalog=descriptors,
            degraded_features=[item.summary for item in descriptors if item.state != "enabled"],
        )

    def portfolio(self) -> ProjectHealthPortfolio:
        return self.project_service.project_health_portfolio()

    def projects(self) -> list[ProjectHealthPortfolioEntry]:
        return self.portfolio().projects

    def project_health(self, project_id: str) -> ProjectHealthSnapshot:
        return self.project_service.project_health(project_id)

    def project_health_snapshot(self, snapshot_id: str) -> ProjectHealthSnapshot | None:
        return self.project_service.project_health_snapshot(snapshot_id)

    def project_health_snapshots(self, project_id: str) -> list[ProjectHealthSnapshot]:
        return self.project_service.project_health_snapshots(project_id)

    def change_portfolio(self) -> ProjectChangePortfolio:
        return self.project_service.project_change_portfolio()

    def change_finding(self, finding_id: str) -> ProjectChangeFinding | None:
        return self.database.get_project_change_finding(finding_id)

    def change_findings(
        self,
        project_id: str,
        *,
        severity: str | None = None,
        direction: str | None = None,
        change_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProjectChangeFinding]:
        findings = self.project_service.list_project_change_findings(project_id)
        if severity:
            findings = [finding for finding in findings if finding.severity == severity]
        if direction:
            findings = [finding for finding in findings if finding.direction == direction]
        if change_type:
            findings = [finding for finding in findings if finding.change_class == change_type]
        if status:
            findings = [finding for finding in findings if finding.status == status]
        return _slice(findings, limit=limit, offset=offset)

    def recent_change_findings(
        self,
        *,
        project_id: str | None = None,
        limit: int = 100,
    ) -> list[ProjectChangeFinding]:
        if project_id:
            return _slice(self.project_service.latest_project_change_findings(project_id), limit=limit, offset=0)
        return self.project_service.recent_project_change_findings(limit=limit)

    def recommendation_portfolio(self) -> ProjectRecommendationPortfolio:
        return self.project_service.project_recommendation_portfolio()

    def recommendations(
        self,
        *,
        project_id: str | None = None,
        priority_tier: str | None = None,
        lifecycle_state: str | None = None,
        blocked_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProjectRecommendation]:
        if project_id is not None:
            recommendations = self.project_service.list_project_recommendations(project_id)
        else:
            recommendations = self.project_service.recommendation_queue(None)
        if priority_tier:
            recommendations = [item for item in recommendations if item.priority_tier == priority_tier]
        if lifecycle_state:
            recommendations = [item for item in recommendations if item.lifecycle_state == lifecycle_state]
        if blocked_only:
            recommendations = [item for item in recommendations if item.lifecycle_state == "blocked"]
        return _slice(recommendations, limit=limit, offset=offset)

    def recommendation(self, recommendation_id: str) -> ProjectRecommendation | None:
        return self.project_service.get_project_recommendation(recommendation_id)

    def work_packages(
        self,
        *,
        project_id: str | None = None,
        approval_state: str | None = None,
        staleness_state: str | None = None,
        risk_classification: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkPackageRecord]:
        packages = self.project_service.work_packages(
            project_id=project_id,
            approval_state=approval_state,
            staleness_state=staleness_state,
        )
        if risk_classification:
            packages = [item for item in packages if item.risk_classification == risk_classification]
        return _slice(packages, limit=limit, offset=offset)

    def work_package(self, work_package_id: str) -> WorkPackageRecord | None:
        return self.project_service.get_work_package(work_package_id)

    def work_package_revision(self, revision_id: str) -> WorkPackageRevisionRecord | None:
        return self.database.get_work_package_revision(revision_id)

    def work_package_revisions(self, work_package_id: str) -> list[WorkPackageRevisionRecord]:
        return self.project_service.work_package_revisions(work_package_id)

    def approval_decisions(self, work_package_id: str) -> list[WorkPackageApprovalDecisionRecord]:
        return self.project_service.work_package_approval_decisions(work_package_id)

    def handoffs(self, work_package_id: str) -> list[WorkPackageHandoffRecord]:
        return self.project_service.work_package_handoffs(work_package_id)

    def outcomes(self, work_package_id: str) -> list[WorkPackageOutcomeRecord]:
        return self.project_service.work_package_outcomes(work_package_id)

    def work_package_summary(self, work_package_id: str) -> dict[str, object]:
        return self.project_service.work_package_summary(work_package_id)

    def work_package_prompt(self, work_package_id: str, revision_number: int | None = None) -> dict[str, object]:
        return {
            "work_package_id": work_package_id,
            "revision_number": revision_number,
            "prompt": self.project_service.render_work_package_prompt(work_package_id, revision_number=revision_number),
        }

    def submit_for_review(self, work_package_id: str, request: ProjectOfficerLifecycleRequest) -> WorkPackageRecord:
        return self.project_service.work_package_submit_for_review(
            work_package_id,
            request.revision_number,
            actor=request.actor,
        )

    def approve(self, work_package_id: str, request: ProjectOfficerLifecycleRequest) -> WorkPackageRecord:
        return self.project_service.work_package_approve(
            work_package_id,
            request.revision_number,
            actor=request.actor,
            human_note=request.human_note,
        )

    def reject(self, work_package_id: str, request: ProjectOfficerLifecycleRequest) -> WorkPackageRecord:
        return self.project_service.work_package_reject(
            work_package_id,
            request.revision_number,
            actor=request.actor,
            human_note=request.human_note,
        )

    def expire(self, work_package_id: str, *, reason: str) -> WorkPackageRecord:
        return self.project_service.expire_work_package(work_package_id, reason)

    def handoff(self, work_package_id: str, request: ProjectOfficerHandoffRequest) -> WorkPackageRecord:
        return self.project_service.work_package_handoff(
            work_package_id,
            request.revision_number,
            approved_by=request.approved_by,
            next_manual_action=request.next_manual_action,
            rollback_reference=request.rollback_reference,
        )

    def record_outcome(self, work_package_id: str, request: ProjectOfficerOutcomeRequest) -> WorkPackageRecord:
        return self.project_service.work_package_record_outcome(
            work_package_id,
            request.revision_number,
            outcome=request.outcome,
            actor=request.actor,
            note=request.note,
        )


def _slice(items: list[Any], *, limit: int, offset: int) -> list[Any]:
    start = max(0, offset)
    end = start + max(1, limit)
    return items[start:end]
