from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from gaia.audit import AuditRecorder
from gaia.config import Settings
from gaia.db import Database
from gaia.models import (
    ProjectChangeFinding,
    ProjectConfig,
    ProjectHealthEvidenceReference,
    ProjectHealthSnapshot,
    ProjectRecommendation,
    ProjectRecommendationPortfolio,
    ProjectRecommendationPortfolioEntry,
    RecommendationBlocker,
    RecommendationBlockerType,
    RecommendationConfidence,
    RecommendationEffort,
    RecommendationLifecycleState,
    RecommendationPriorityTier,
    RecommendationReversibility,
    RecommendationScoreBreakdown,
    RecommendationType,
    RecommendationUrgency,
    utc_now,
)

RECOMMENDATION_POLICY_VERSION = "gaia-v0.9-b3-v1"
RECOMMENDATION_SCHEMA_VERSION = 1

_STATE_ORDER: dict[str, int] = {
    "active": 0,
    "blocked": 1,
    "deferred": 2,
    "resolved": 3,
    "superseded": 4,
    "stale": 5,
}
_PRIORITY_ORDER: dict[str, int] = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
_CONFIDENCE_SCORE: dict[str, int] = {"high": 10, "medium": 6, "low": 2, "unknown": 0}
_EFFORT_SCORE: dict[str, int] = {"tiny": 0, "small": -2, "medium": -5, "large": -9, "unknown": -3}
_REVERSIBILITY_SCORE: dict[str, int] = {"easy": 5, "moderate": 3, "difficult": -2, "unknown": 0}
_URGENCY_SCORE: dict[str, int] = {"immediate": 20, "soon": 14, "normal": 8, "low": 2, "unknown": 0}
_FRESHNESS_SCORE: dict[str, int] = {"fresh": 5, "aging": 2, "stale": 0, "unknown": 0}


@dataclass(slots=True)
class _Candidate:
    recommendation_type: RecommendationType
    semantic_key: str
    issue_key: str
    title: str
    concise_summary: str
    rationale: str
    why_it_matters: str
    why_it_received_this_score: str
    reasons_to_proceed: list[str]
    reasons_not_to_proceed: list[str]
    blockers: list[RecommendationBlocker]
    dependency_semantic_keys: list[str]
    evidence_references: list[ProjectHealthEvidenceReference]
    source_finding_ids: list[str]
    source_comparison_ids: list[str]
    source_snapshot_ids: list[str]
    evidence_fingerprints: list[str]
    evidence_freshness: str
    confidence: RecommendationConfidence
    urgency_category: RecommendationUrgency
    effort_category: RecommendationEffort
    reversibility_category: RecommendationReversibility
    severity_contribution: int
    user_impact_contribution: int
    release_impact_contribution: int
    safety_impact_contribution: int
    dependency_impact_contribution: int
    freshness_contribution: int
    lifecycle_state: RecommendationLifecycleState
    uncertainty: str


class RecommendationService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        audit: AuditRecorder,
        *,
        policy_version: str = RECOMMENDATION_POLICY_VERSION,
    ) -> None:
        self.settings = settings
        self.database = database
        self.audit = audit
        self.policy_version = policy_version

    def get_project(self, project_id: str) -> ProjectConfig:
        try:
            return self.settings.projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def get_recommendation(self, recommendation_id: str) -> ProjectRecommendation | None:
        recommendation = self.database.get_project_recommendation(recommendation_id)
        if recommendation is not None:
            self._validate_schema(recommendation)
        return recommendation

    def list_project_recommendations(self, project_id: str) -> list[ProjectRecommendation]:
        self.get_project(project_id)
        recommendations = self.database.list_project_recommendations(project_id)
        for recommendation in recommendations:
            self._validate_schema(recommendation)
        return sorted(recommendations, key=_queue_sort_key)

    def generate_project_recommendations(self, project_id: str) -> list[ProjectRecommendation]:
        project = self.get_project(project_id)
        return self._refresh_project_recommendations(project)

    def refresh_all_project_recommendations(self) -> list[ProjectRecommendation]:
        refreshed: list[ProjectRecommendation] = []
        for project in sorted(self.settings.projects.values(), key=lambda item: item.project_id):
            if project.enabled:
                refreshed.extend(self._refresh_project_recommendations(project))
        return refreshed

    def recommendation_queue(self, project_id: str | None = None) -> list[ProjectRecommendation]:
        if project_id is not None:
            recommendations = self.generate_project_recommendations(project_id)
            validate_recommendation_dependencies(recommendations)
            return sorted(recommendations, key=_queue_sort_key)
        self.refresh_all_project_recommendations()
        project_ids = sorted(project.project_id for project in self.settings.projects.values() if project.enabled)
        recommendations = self.database.list_recommendations_for_projects(project_ids)
        for recommendation in recommendations:
            self._validate_schema(recommendation)
        validate_recommendation_dependencies(recommendations)
        return sorted(recommendations, key=_queue_sort_key)

    def project_recommendation_portfolio(self) -> ProjectRecommendationPortfolio:
        self.refresh_all_project_recommendations()
        projects: list[ProjectRecommendationPortfolioEntry] = []
        overall_priority: Counter[str] = Counter()
        overall_state: Counter[str] = Counter()

        for project in sorted(self.settings.projects.values(), key=lambda item: item.project_id):
            if not project.enabled:
                continue
            recommendations = self.list_project_recommendations(project.project_id)
            overall_priority.update(item.priority_tier for item in recommendations)
            overall_state.update(item.lifecycle_state for item in recommendations)
            active = [item for item in recommendations if item.lifecycle_state in {"active", "blocked", "deferred"}]
            active_sorted = sorted(active, key=_queue_sort_key)
            latest = active_sorted[0] if active_sorted else (recommendations[0] if recommendations else None)
            projects.append(
                ProjectRecommendationPortfolioEntry(
                    project_id=project.project_id,
                    project_name=project.name,
                    latest_recommendation_id=latest.recommendation_id if latest else None,
                    latest_created_timestamp=latest.created_timestamp if latest else None,
                    latest_priority_tier=latest.priority_tier if latest else "P4",
                    latest_lifecycle_state=latest.lifecycle_state if latest else "stale",
                    recommendation_count=len(recommendations),
                    active_recommendation_count=sum(item.lifecycle_state == "active" for item in recommendations),
                    blocked_recommendation_count=sum(item.lifecycle_state == "blocked" for item in recommendations),
                    counts_by_priority=dict(sorted(Counter(item.priority_tier for item in recommendations).items(), key=lambda item: _PRIORITY_ORDER.get(item[0], 99))),
                    counts_by_state=dict(sorted(Counter(item.lifecycle_state for item in recommendations).items(), key=lambda item: _STATE_ORDER.get(item[0], 99))),
                    latest_recommendations=active_sorted[:3],
                )
            )

        queue = sorted(self.database.list_recommendations_for_projects([item.project_id for item in self.settings.projects.values() if item.enabled]), key=_queue_sort_key)
        validate_recommendation_dependencies(queue)
        return ProjectRecommendationPortfolio(
            generated_at=utc_now(),
            projects=projects,
            recommendation_queue=queue,
            counts_by_priority=dict(sorted(overall_priority.items(), key=lambda item: _PRIORITY_ORDER.get(item[0], 99))),
            counts_by_state=dict(sorted(overall_state.items(), key=lambda item: _STATE_ORDER.get(item[0], 99))),
        )

    def _refresh_project_recommendations(self, project: ProjectConfig) -> list[ProjectRecommendation]:
        health = self.database.latest_project_health_snapshot(project.project_id)
        findings = self.database.latest_project_change_findings(project.project_id)
        candidates = self._build_candidates(project, health, findings)
        if not candidates:
            return []

        candidate_by_semantic = {candidate.semantic_key: candidate for candidate in candidates}
        existing_by_semantic = {
            recommendation.semantic_fingerprint: recommendation
            for recommendation in self.database.list_project_recommendations(project.project_id)
        }

        semantic_to_id = {key: _recommendation_id(key) for key in candidate_by_semantic}
        persisted: list[ProjectRecommendation] = []
        current_semantics = set(candidate_by_semantic)
        for candidate in candidates:
            existing = existing_by_semantic.get(candidate.semantic_key)
            recommendation = self._build_recommendation(
                project=project,
                health=health,
                candidate=candidate,
                recommendation_id=semantic_to_id[candidate.semantic_key],
                dependency_ids=[semantic_to_id[key] for key in candidate.dependency_semantic_keys if key in semantic_to_id],
                existing=existing,
            )
            self.database.insert_project_recommendation(recommendation)
            audit_event = self.audit.record(
                category="recommendation",
                operation="refresh_project_recommendation",
                project_id=project.project_id,
                outcome="success",
                metadata={
                    "recommendation_id": recommendation.recommendation_id,
                    "recommendation_type": recommendation.recommendation_type,
                    "priority_tier": recommendation.priority_tier,
                    "deterministic_score": recommendation.deterministic_score,
                },
            )
            recommendation.audit_event_id = audit_event.event_id
            self.database.update_project_recommendation_audit_event(recommendation.recommendation_id, audit_event.event_id)
            persisted.append(recommendation)

        for existing in self.database.list_project_recommendations(project.project_id):
            if existing.semantic_fingerprint in current_semantics:
                continue
            if existing.lifecycle_state in {"resolved", "superseded", "stale"}:
                continue
            lifecycle_state: RecommendationLifecycleState = "resolved"
            if existing.recommendation_type == "insufficient_evidence":
                lifecycle_state = "stale"
            self.database.update_project_recommendation_state(
                existing.recommendation_id,
                lifecycle_state=lifecycle_state,
                updated_timestamp=utc_now(),
            )

        refreshed = self.database.list_project_recommendations(project.project_id)
        for recommendation in refreshed:
            self._validate_schema(recommendation)
        return sorted(refreshed, key=_queue_sort_key)

    def _build_candidates(
        self,
        project: ProjectConfig,
        health: ProjectHealthSnapshot | None,
        findings: list[ProjectChangeFinding],
    ) -> list[_Candidate]:
        if health is None:
            return [_insufficient_evidence_candidate(project)]

        payload = health.normalized_payload
        git_state = dict(payload.get("git_state", {}))
        configured = dict(payload.get("configured_evidence", {}))
        freshness = str(dict(configured.get("evidence_freshness", {})).get("state", "unknown"))
        missing_paths = list(configured.get("missing_important_paths", []))
        current_findings = [finding for finding in findings if finding.current_snapshot_id == health.snapshot_id]
        findings_by_class: dict[str, list[ProjectChangeFinding]] = defaultdict(list)
        for finding in current_findings:
            findings_by_class[finding.change_class].append(finding)

        candidates: list[_Candidate] = []
        if health.normalized_status == "blocked":
            candidates.append(_blocking_health_candidate(project, health, freshness, git_state))
        if "working_tree_dirty" in health.reason_codes or findings_by_class.get("working_tree_change"):
            candidates.append(_candidate_from_findings(project, health, findings_by_class["working_tree_change"], recommendation_type="review_uncommitted_project_changes", issue_key="working_tree_dirty", title="Review uncommitted project changes.", concise_summary="The working tree contains tracked or untracked changes that deserve human attention.", rationale="The latest health evidence shows that the working tree is no longer clean.", why_it_matters="Uncommitted changes can hide the canonical repository state and complicate later comparisons.", why_it_received_this_score="The score reflects a moderate-severity working-tree change with good evidence quality.", reasons_to_proceed=["Working-tree changes are directly visible and can be reviewed safely."], reasons_not_to_proceed=["The issue is less urgent if the project is already blocked by a higher-order condition."], freshness=freshness, urgency_category="soon", effort_category="small", reversibility_category="easy", severity_contribution=20, user_impact_contribution=_project_sensitivity_weight(project), release_impact_contribution=10, safety_impact_contribution=5, dependency_impact_contribution=5, freshness_contribution=_freshness_score_for_candidate("review_uncommitted_project_changes", freshness), confidence=_confidence_from_findings(findings_by_class["working_tree_change"], freshness), uncertainty="Evidence is strong if the latest snapshot is fresh and the change finding is present."))
        if "important_paths_missing" in health.reason_codes:
            candidates.append(_candidate_from_findings(project, health, findings_by_class["important_path_change"], recommendation_type="verify_removal_of_configured_important_project_path", issue_key="important_paths_" + "-".join(sorted(missing_paths or ["missing"])), title="Verify removal of configured important project path.", concise_summary="A configured important path is missing and should be reviewed explicitly.", rationale="The current health snapshot reports that one or more configured important paths are absent.", why_it_matters="Missing important paths can invalidate the evidence used by other planning decisions.", why_it_received_this_score="The score reflects a path-level configuration issue with moderate impact and clear evidence.", reasons_to_proceed=["The missing path is explicitly configured as important."], reasons_not_to_proceed=["Other recommendations should wait if the evidence itself is stale."], freshness=freshness, urgency_category="soon", effort_category="medium", reversibility_category="easy", severity_contribution=18, user_impact_contribution=_project_sensitivity_weight(project), release_impact_contribution=12, safety_impact_contribution=4, dependency_impact_contribution=5, freshness_contribution=_freshness_score_for_candidate("verify_removal_of_configured_important_project_path", freshness), confidence=_confidence_from_findings(findings_by_class["important_path_change"], freshness), uncertainty="Confidence is strongest when the missing path is confirmed in the latest fresh health snapshot."))
        if "branch_divergence" in health.reason_codes or findings_by_class.get("upstream_divergence"):
            candidates.append(_candidate_from_findings(project, health, findings_by_class["upstream_divergence"], recommendation_type="review_upstream_branch_divergence", issue_key="upstream_divergence", title="Review upstream branch divergence.", concise_summary="The branch diverges from its upstream and should be reviewed before relying on it.", rationale="Branch divergence was detected in the latest health or change evidence.", why_it_matters="Ahead or behind divergence can affect release planning and evidence freshness.", why_it_received_this_score="The score reflects a meaningful Git-state divergence with release relevance.", reasons_to_proceed=["Branch divergence is a canonical signal of repository drift."], reasons_not_to_proceed=["If the evidence is stale, a fresh capture should happen first."], freshness=freshness, urgency_category="soon", effort_category="small", reversibility_category="moderate", severity_contribution=16, user_impact_contribution=_project_sensitivity_weight(project), release_impact_contribution=15, safety_impact_contribution=5, dependency_impact_contribution=5, freshness_contribution=_freshness_score_for_candidate("review_upstream_branch_divergence", freshness), confidence=_confidence_from_findings(findings_by_class["upstream_divergence"], freshness), uncertainty="Confidence is high when the branch divergence appears in the latest fresh project-health snapshot."))
        if git_state.get("detached_head") or findings_by_class.get("head_change"):
            candidates.append(_candidate_from_findings(project, health, findings_by_class["head_change"], recommendation_type="review_repository_head_change", issue_key="detached_head" if git_state.get("detached_head") else "head_change", title="Review repository HEAD movement.", concise_summary="The repository HEAD moved and should be checked for context.", rationale="The latest evidence shows the repository HEAD changed or is detached.", why_it_matters="Unexpected HEAD movement can affect reproducibility and downstream comparisons.", why_it_received_this_score="The score is moderate because HEAD changes are important but often easy to inspect.", reasons_to_proceed=["The change is directly tied to the canonical repository state."], reasons_not_to_proceed=["The issue may already be explained by a higher-order project-health blocker."], freshness=freshness, urgency_category="normal", effort_category="tiny", reversibility_category="moderate", severity_contribution=12, user_impact_contribution=_project_sensitivity_weight(project), release_impact_contribution=10, safety_impact_contribution=3, dependency_impact_contribution=3, freshness_contribution=_freshness_score_for_candidate("review_repository_head_change", freshness), confidence=_confidence_from_findings(findings_by_class["head_change"], freshness), uncertainty="The recommendation is precise when the head change is corroborated by the latest snapshot."))
        if freshness == "stale":
            candidates.append(_stale_evidence_candidate(project, health, findings))
        if findings_by_class.get("configuration_change"):
            candidates.append(_candidate_from_findings(project, health, findings_by_class["configuration_change"], recommendation_type="review_project_configuration_change", issue_key="configuration_change", title="Review project configuration change.", concise_summary="The project configuration fingerprint changed and should be reviewed.", rationale="The latest project-health evidence reports a configuration fingerprint change.", why_it_matters="Configuration drift can invalidate comparisons and change the meaning of later findings.", why_it_received_this_score="The score reflects a cross-cutting configuration change with moderate release impact.", reasons_to_proceed=["Configuration drift can change the interpretation of every downstream finding."], reasons_not_to_proceed=["The change may already be superseded if a higher-order blocker is present."], freshness=freshness, urgency_category="normal", effort_category="medium", reversibility_category="moderate", severity_contribution=18, user_impact_contribution=_project_sensitivity_weight(project), release_impact_contribution=12, safety_impact_contribution=4, dependency_impact_contribution=5, freshness_contribution=_freshness_score_for_candidate("review_project_configuration_change", freshness), confidence=_confidence_from_findings(findings_by_class["configuration_change"], freshness), uncertainty="The configuration fingerprint provides strong evidence even when individual field deltas are not expanded."))
        if health.normalized_status == "unknown" and not candidates:
            candidates.append(_insufficient_evidence_candidate(project, health))
        return _deduplicate_candidates(candidates)

    def _build_recommendation(
        self,
        *,
        project: ProjectConfig,
        health: ProjectHealthSnapshot | None,
        candidate: _Candidate,
        recommendation_id: str,
        dependency_ids: list[str],
        existing: ProjectRecommendation | None,
    ) -> ProjectRecommendation:
        score_breakdown = _score_breakdown(project, candidate, dependency_ids)
        priority_tier = _priority_tier(candidate, score_breakdown)
        current_fingerprint = _content_fingerprint(project, candidate, score_breakdown, dependency_ids)
        created_timestamp = existing.created_timestamp if existing is not None else utc_now()
        changed = (
            existing is None
            or existing.content_fingerprint != current_fingerprint
            or existing.lifecycle_state != candidate.lifecycle_state
            or existing.priority_tier != priority_tier
        )
        updated_timestamp = utc_now() if changed else (existing.updated_timestamp if existing is not None else created_timestamp)
        normalized_payload = _recommendation_payload(
            project=project,
            health=health,
            candidate=candidate,
            recommendation_id=recommendation_id,
            dependency_ids=dependency_ids,
            score_breakdown=score_breakdown,
            priority_tier=priority_tier,
            created_timestamp=created_timestamp,
            updated_timestamp=updated_timestamp,
            content_fingerprint=current_fingerprint,
        )
        recommendation = ProjectRecommendation(
            recommendation_id=recommendation_id,
            schema_version=RECOMMENDATION_SCHEMA_VERSION,
            project_id=project.project_id,
            recommendation_type=candidate.recommendation_type,
            recommendation_policy_version=self.policy_version,
            created_timestamp=created_timestamp,
            updated_timestamp=updated_timestamp,
            lifecycle_state=candidate.lifecycle_state,
            priority_tier=priority_tier,
            deterministic_score=score_breakdown.total_score,
            score_breakdown=score_breakdown,
            title=candidate.title,
            concise_summary=candidate.concise_summary,
            rationale=candidate.rationale,
            why_it_matters=candidate.why_it_matters,
            why_it_received_this_score=candidate.why_it_received_this_score,
            reasons_to_proceed=candidate.reasons_to_proceed,
            reasons_not_to_proceed=candidate.reasons_not_to_proceed,
            blockers=candidate.blockers,
            dependencies=dependency_ids,
            uncertainty=candidate.uncertainty,
            source_finding_ids=_ordered_unique(candidate.source_finding_ids),
            source_comparison_ids=_ordered_unique(candidate.source_comparison_ids),
            source_snapshot_ids=_ordered_unique(candidate.source_snapshot_ids),
            evidence_fingerprints=_ordered_unique(candidate.evidence_fingerprints),
            evidence_freshness=candidate.evidence_freshness,
            evidence_references=candidate.evidence_references,
            semantic_fingerprint=candidate.semantic_key,
            content_fingerprint=current_fingerprint,
            provenance_reference=health.provenance_reference if health is not None else None,
            supersedes_recommendation_id=existing.recommendation_id if existing is not None and existing.content_fingerprint != current_fingerprint else None,
            normalized_payload=normalized_payload,
        )
        return recommendation

    def _validate_schema(self, recommendation: ProjectRecommendation) -> None:
        if recommendation.schema_version != RECOMMENDATION_SCHEMA_VERSION:
            raise ValueError(f"Unsupported recommendation schema version: {recommendation.schema_version}")


def _blocking_health_candidate(
    project: ProjectConfig,
    health: ProjectHealthSnapshot,
    freshness: str,
    git_state: dict[str, Any],
) -> _Candidate:
    blocker_type: RecommendationBlockerType = (
        "project_root_unavailable"
        if any("root" in condition.lower() for condition in health.blocking_conditions)
        else "required_human_decision_missing"
    )
    blocker = RecommendationBlocker(
        blocker_type=blocker_type,
        blocker_description=health.blocking_conditions[0] if health.blocking_conditions else "The project is blocked.",
        required_condition="The blocking project-health condition must be addressed.",
        evidence_ids=[health.snapshot_id],
        details={"reason_codes": list(health.reason_codes), "git_state": git_state},
    )
    return _candidate(
        project=project,
        health=health,
        recommendation_type="review_blocking_project_health_condition",
        issue_key="health_blocked",
        title="Review blocking project-health condition.",
        concise_summary="The project is blocked in the canonical health model and needs human review.",
        rationale="The latest project-health snapshot reports a blocking condition that should be reviewed first.",
        why_it_matters="Blocked health means the repository is not in a safe or fully inspectable state.",
        why_it_received_this_score="Blocking health conditions dominate the score because they can prevent all other work from being trustworthy.",
        reasons_to_proceed=["The project is explicitly blocked, so the blocker should be reviewed before lower-priority work."],
        reasons_not_to_proceed=["Other recommendations may be premature until the blocking condition is understood."],
        blockers=[blocker],
        dependency_semantic_keys=[],
        evidence_references=_evidence_references(health, []),
        source_finding_ids=[],
        source_comparison_ids=[],
        source_snapshot_ids=[health.snapshot_id],
        evidence_fingerprints=[health.content_fingerprint],
        evidence_freshness=freshness,
        findings=[],
        urgency_category="immediate",
        effort_category="small",
        reversibility_category="moderate",
        severity_contribution=35,
        user_impact_contribution=_project_sensitivity_weight(project),
        release_impact_contribution=20,
        safety_impact_contribution=20,
        dependency_impact_contribution=0,
        freshness_contribution=_freshness_score_for_candidate("review_blocking_project_health_condition", freshness),
        confidence=_confidence_from_health(health),
        uncertainty="High confidence because the blocking state is directly captured in the latest health snapshot.",
        lifecycle_state="active",
    )


def _stale_evidence_candidate(project: ProjectConfig, health: ProjectHealthSnapshot, findings: list[ProjectChangeFinding]) -> _Candidate:
    blocker = RecommendationBlocker(
        blocker_type="evidence_too_stale",
        blocker_description="The latest health evidence is stale.",
        required_condition="Capture fresh project-health evidence before trusting the current state.",
        evidence_ids=[health.snapshot_id],
        details={"freshness": "stale"},
    )
    return _candidate(
        project=project,
        health=health,
        recommendation_type="refresh_project_evidence_before_relying_on_state",
        issue_key="stale_evidence",
        title="Refresh project evidence before relying on the current state.",
        concise_summary="The latest project evidence is stale and should be refreshed first.",
        rationale="The current evidence freshness state no longer supports safe prioritisation without a refresh.",
        why_it_matters="Stale evidence lowers confidence in every other recommendation derived from the project.",
        why_it_received_this_score="The score is elevated because fresh evidence is a prerequisite for dependable prioritisation.",
        reasons_to_proceed=["Fresh evidence unlocks higher-confidence recommendations."],
        reasons_not_to_proceed=["The evidence age means other recommendations should not outrank evidence refresh."],
        blockers=[blocker],
        dependency_semantic_keys=[],
        evidence_references=_evidence_references(health, findings),
        source_finding_ids=[finding.finding_id for finding in findings],
        source_comparison_ids=_ordered_unique([finding.comparison_id for finding in findings]),
        source_snapshot_ids=_ordered_unique([health.snapshot_id, *[finding.previous_snapshot_id for finding in findings], *[finding.current_snapshot_id for finding in findings]]),
        evidence_fingerprints=_ordered_unique([health.content_fingerprint, *[finding.content_fingerprint for finding in findings]]),
        evidence_freshness="stale",
        findings=findings,
        urgency_category="immediate",
        effort_category="tiny",
        reversibility_category="easy",
        severity_contribution=14,
        user_impact_contribution=_project_sensitivity_weight(project),
        release_impact_contribution=8,
        safety_impact_contribution=5,
        dependency_impact_contribution=0,
        freshness_contribution=15,
        confidence=_confidence_from_findings(findings, "stale"),
        uncertainty="The freshness signal is explicit and should be refreshed before lower-confidence recommendations.",
        lifecycle_state="active",
    )


def _insufficient_evidence_candidate(project: ProjectConfig, health: ProjectHealthSnapshot | None = None) -> _Candidate:
    evidence_references = _evidence_references(health, []) if health is not None else []
    blocker = RecommendationBlocker(
        blocker_type="insufficient_evidence",
        blocker_description="No structured project-health evidence is available yet.",
        required_condition="Capture at least one project-health snapshot before prioritising work.",
        evidence_ids=[health.snapshot_id] if health is not None else [],
        details={"project_id": project.project_id},
    )
    return _candidate(
        project=project,
        health=health,
        recommendation_type="insufficient_evidence",
        issue_key="no_snapshot",
        title="Capture project evidence before prioritising work.",
        concise_summary="The project does not yet have enough structured evidence for safe prioritisation.",
        rationale="A valid health snapshot is required before the project can be ranked confidently.",
        why_it_matters="Without a snapshot, recommendations would be speculative rather than evidence-based.",
        why_it_received_this_score="The score stays low so evidence gaps do not outrank genuine actionable issues.",
        reasons_to_proceed=["Capturing evidence is the prerequisite for deterministic prioritisation."],
        reasons_not_to_proceed=["There is insufficient structured evidence to justify a higher-priority recommendation."],
        blockers=[blocker],
        dependency_semantic_keys=[],
        evidence_references=evidence_references,
        source_finding_ids=[],
        source_comparison_ids=[],
        source_snapshot_ids=[health.snapshot_id] if health is not None else [],
        evidence_fingerprints=[health.content_fingerprint] if health is not None else [],
        evidence_freshness="unknown",
        findings=[],
        urgency_category="immediate",
        effort_category="tiny",
        reversibility_category="easy",
        severity_contribution=6,
        user_impact_contribution=_project_sensitivity_weight(project),
        release_impact_contribution=2,
        safety_impact_contribution=2,
        dependency_impact_contribution=0,
        freshness_contribution=0,
        confidence="unknown",
        uncertainty="No project-health snapshot exists yet.",
        lifecycle_state="blocked",
    )


def _candidate_from_findings(
    project: ProjectConfig,
    health: ProjectHealthSnapshot,
    findings: list[ProjectChangeFinding],
    *,
    recommendation_type: RecommendationType,
    issue_key: str,
    title: str,
    concise_summary: str,
    rationale: str,
    why_it_matters: str,
    why_it_received_this_score: str,
    reasons_to_proceed: list[str],
    reasons_not_to_proceed: list[str],
    blockers: list[RecommendationBlocker] | None = None,
    dependency_semantic_keys: list[str] | None = None,
    freshness: str,
    urgency_category: RecommendationUrgency,
    effort_category: RecommendationEffort,
    reversibility_category: RecommendationReversibility,
    severity_contribution: int,
    user_impact_contribution: int,
    release_impact_contribution: int,
    safety_impact_contribution: int,
    dependency_impact_contribution: int,
    freshness_contribution: int,
    confidence: RecommendationConfidence,
    uncertainty: str,
) -> _Candidate:
    blockers = list(blockers or [])
    dependency_semantic_keys = list(dependency_semantic_keys or [])
    if not blockers and freshness == "stale" and recommendation_type != "refresh_project_evidence_before_relying_on_state":
        blockers.append(
            RecommendationBlocker(
                blocker_type="evidence_too_stale",
                blocker_description="The latest evidence is stale.",
                required_condition="Capture fresh evidence before relying on this recommendation.",
                evidence_ids=[health.snapshot_id],
                details={"freshness": freshness},
            )
        )
        dependency_semantic_keys.append(_semantic_key(health.project_id, "refresh_project_evidence_before_relying_on_state", "stale_evidence"))
    if health.normalized_status == "blocked" and recommendation_type != "review_blocking_project_health_condition":
        dependency_semantic_keys.append(_semantic_key(health.project_id, "review_blocking_project_health_condition", "health_blocked"))
    return _candidate(
        project=project,
        health=health,
        recommendation_type=recommendation_type,
        issue_key=issue_key,
        title=title,
        concise_summary=concise_summary,
        rationale=rationale,
        why_it_matters=why_it_matters,
        why_it_received_this_score=why_it_received_this_score,
        reasons_to_proceed=reasons_to_proceed,
        reasons_not_to_proceed=reasons_not_to_proceed,
        blockers=blockers,
        dependency_semantic_keys=sorted(set(dependency_semantic_keys)),
        evidence_references=_evidence_references(health, findings),
        source_finding_ids=[finding.finding_id for finding in findings],
        source_comparison_ids=_ordered_unique([finding.comparison_id for finding in findings]),
        source_snapshot_ids=_ordered_unique([health.snapshot_id, *[finding.previous_snapshot_id for finding in findings], *[finding.current_snapshot_id for finding in findings]]),
        evidence_fingerprints=_ordered_unique([health.content_fingerprint, *[finding.content_fingerprint for finding in findings]]),
        evidence_freshness=freshness,
        findings=findings,
        confidence=confidence,
        urgency_category=urgency_category,
        effort_category=effort_category,
        reversibility_category=reversibility_category,
        severity_contribution=severity_contribution,
        user_impact_contribution=user_impact_contribution,
        release_impact_contribution=release_impact_contribution,
        safety_impact_contribution=safety_impact_contribution,
        dependency_impact_contribution=dependency_impact_contribution,
        freshness_contribution=freshness_contribution,
        lifecycle_state="blocked" if blockers else ("superseded" if health.normalized_status == "blocked" else "active"),
        uncertainty=uncertainty,
    )


def _candidate(
    *,
    project: ProjectConfig,
    health: ProjectHealthSnapshot | None,
    recommendation_type: RecommendationType,
    issue_key: str,
    title: str,
    concise_summary: str,
    rationale: str,
    why_it_matters: str,
    why_it_received_this_score: str,
    reasons_to_proceed: list[str],
    reasons_not_to_proceed: list[str],
    blockers: list[RecommendationBlocker],
    dependency_semantic_keys: list[str],
    evidence_references: list[ProjectHealthEvidenceReference],
    source_finding_ids: list[str],
    source_comparison_ids: list[str],
    source_snapshot_ids: list[str],
    evidence_fingerprints: list[str],
    evidence_freshness: str,
    findings: list[ProjectChangeFinding],
    urgency_category: RecommendationUrgency,
    effort_category: RecommendationEffort,
    reversibility_category: RecommendationReversibility,
    severity_contribution: int,
    user_impact_contribution: int,
    release_impact_contribution: int,
    safety_impact_contribution: int,
    dependency_impact_contribution: int,
    freshness_contribution: int,
    confidence: RecommendationConfidence,
    uncertainty: str,
    lifecycle_state: RecommendationLifecycleState,
) -> _Candidate:
    health = health or _placeholder_health(project)
    semantic_key = _semantic_key(project.project_id, recommendation_type, issue_key)
    return _Candidate(
        recommendation_type=recommendation_type,
        semantic_key=semantic_key,
        issue_key=issue_key,
        title=title,
        concise_summary=concise_summary,
        rationale=rationale,
        why_it_matters=why_it_matters,
        why_it_received_this_score=why_it_received_this_score,
        reasons_to_proceed=reasons_to_proceed,
        reasons_not_to_proceed=reasons_not_to_proceed,
        blockers=blockers,
        dependency_semantic_keys=dependency_semantic_keys,
        evidence_references=evidence_references,
        source_finding_ids=source_finding_ids,
        source_comparison_ids=source_comparison_ids,
        source_snapshot_ids=source_snapshot_ids,
        evidence_fingerprints=evidence_fingerprints,
        evidence_freshness=evidence_freshness,
        confidence=confidence,
        urgency_category=urgency_category,
        effort_category=effort_category,
        reversibility_category=reversibility_category,
        severity_contribution=severity_contribution,
        user_impact_contribution=user_impact_contribution,
        release_impact_contribution=release_impact_contribution,
        safety_impact_contribution=safety_impact_contribution,
        dependency_impact_contribution=dependency_impact_contribution,
        freshness_contribution=freshness_contribution,
        lifecycle_state=lifecycle_state,
        uncertainty=uncertainty,
    )


def _evidence_references(health: ProjectHealthSnapshot, findings: list[ProjectChangeFinding]) -> list[ProjectHealthEvidenceReference]:
    references = [
        ProjectHealthEvidenceReference(
            evidence_kind="project_health_snapshot",
            evidence_id=health.snapshot_id,
            description="Latest project-health snapshot",
            freshness=_health_freshness(health),
            details={"status": health.normalized_status, "fingerprint": health.content_fingerprint},
        )
    ]
    for finding in findings:
        references.append(
            ProjectHealthEvidenceReference(
                evidence_kind="project_change_finding",
                evidence_id=finding.finding_id,
                description=f"Change finding: {finding.change_class}",
                freshness="captured",
                details={
                    "comparison_id": finding.comparison_id,
                    "severity": finding.severity,
                    "direction": finding.direction,
                    "fingerprint": finding.content_fingerprint,
                },
            )
        )
    return references


def _placeholder_health(project: ProjectConfig) -> ProjectHealthSnapshot:
    return ProjectHealthSnapshot(
        snapshot_id=f"placeholder-{project.project_id}",
        project_id=project.project_id,
        project_name=project.name,
        project_root=str(project.root),
        project_configuration_fingerprint=project.config_fingerprint(),
        normalized_status="unknown",
    )


def _health_freshness(health: ProjectHealthSnapshot) -> str:
    configured = dict(health.normalized_payload.get("configured_evidence", {}))
    freshness = dict(configured.get("evidence_freshness", {}))
    return str(freshness.get("state", "unknown"))


def _priority_tier(candidate: _Candidate, score_breakdown: RecommendationScoreBreakdown) -> RecommendationPriorityTier:
    if candidate.recommendation_type == "review_blocking_project_health_condition" and any(blocker.blocker_type == "project_root_unavailable" for blocker in candidate.blockers):
        return "P0"
    if score_breakdown.total_score >= 90:
        return "P0"
    if score_breakdown.total_score >= 75:
        return "P1"
    if score_breakdown.total_score >= 55:
        return "P2"
    if score_breakdown.total_score >= 35:
        return "P3"
    return "P4"


def _score_breakdown(project: ProjectConfig, candidate: _Candidate, dependency_ids: list[str]) -> RecommendationScoreBreakdown:
    dependency_bonus = min(10, len(dependency_ids) * 3)
    total = (
        candidate.severity_contribution
        + candidate.user_impact_contribution
        + candidate.release_impact_contribution
        + candidate.safety_impact_contribution
        + candidate.dependency_impact_contribution
        + dependency_bonus
        + _CONFIDENCE_SCORE.get(candidate.confidence, 0)
        + _EFFORT_SCORE.get(candidate.effort_category, 0)
        + _REVERSIBILITY_SCORE.get(candidate.reversibility_category, 0)
        + _URGENCY_SCORE.get(candidate.urgency_category, 0)
        + _FRESHNESS_SCORE.get(candidate.evidence_freshness, 0)
    )
    return RecommendationScoreBreakdown(
        urgency_category=candidate.urgency_category,
        effort_category=candidate.effort_category,
        reversibility_category=candidate.reversibility_category,
        severity_contribution=candidate.severity_contribution,
        urgency_contribution=_URGENCY_SCORE.get(candidate.urgency_category, 0),
        user_impact_contribution=candidate.user_impact_contribution,
        release_impact_contribution=candidate.release_impact_contribution,
        safety_impact_contribution=candidate.safety_impact_contribution,
        dependency_impact_contribution=candidate.dependency_impact_contribution + dependency_bonus,
        confidence_contribution=_CONFIDENCE_SCORE.get(candidate.confidence, 0),
        effort_contribution=_EFFORT_SCORE.get(candidate.effort_category, 0),
        reversibility_contribution=_REVERSIBILITY_SCORE.get(candidate.reversibility_category, 0),
        freshness_contribution=_freshness_score(candidate),
        total_score=max(0, min(100, total)),
    )


def _freshness_score(candidate: _Candidate) -> int:
    if candidate.recommendation_type == "refresh_project_evidence_before_relying_on_state":
        return {"stale": 15, "aging": 10, "fresh": 0, "unknown": 0}.get(candidate.evidence_freshness, 0)
    return _FRESHNESS_SCORE.get(candidate.evidence_freshness, 0)


def _content_fingerprint(project: ProjectConfig, candidate: _Candidate, score_breakdown: RecommendationScoreBreakdown, dependency_ids: list[str]) -> str:
    payload = {
        "policy_version": RECOMMENDATION_POLICY_VERSION,
        "project_id": project.project_id,
        "recommendation_type": candidate.recommendation_type,
        "issue_key": candidate.issue_key,
        "source_finding_ids": candidate.source_finding_ids,
        "source_comparison_ids": candidate.source_comparison_ids,
        "source_snapshot_ids": candidate.source_snapshot_ids,
        "evidence_fingerprints": candidate.evidence_fingerprints,
        "dependencies": dependency_ids,
        "score_breakdown": score_breakdown.model_dump(mode="json"),
        "lifecycle_state": candidate.lifecycle_state,
    }
    return _sha256_json(payload)


def _recommendation_payload(
    *,
    project: ProjectConfig,
    health: ProjectHealthSnapshot | None,
    candidate: _Candidate,
    recommendation_id: str,
    dependency_ids: list[str],
    score_breakdown: RecommendationScoreBreakdown,
    priority_tier: RecommendationPriorityTier,
    created_timestamp: datetime,
    updated_timestamp: datetime,
    content_fingerprint: str,
) -> dict[str, Any]:
    return {
        "recommendation_id": recommendation_id,
        "schema_version": RECOMMENDATION_SCHEMA_VERSION,
        "project_id": project.project_id,
        "recommendation_type": candidate.recommendation_type,
        "recommendation_policy_version": RECOMMENDATION_POLICY_VERSION,
        "created_timestamp": created_timestamp.isoformat(),
        "updated_timestamp": updated_timestamp.isoformat(),
        "lifecycle_state": candidate.lifecycle_state,
        "priority_tier": priority_tier,
        "deterministic_score": score_breakdown.total_score,
        "score_breakdown": score_breakdown.model_dump(mode="json"),
        "title": candidate.title,
        "concise_summary": candidate.concise_summary,
        "rationale": candidate.rationale,
        "why_it_matters": candidate.why_it_matters,
        "why_it_received_this_score": candidate.why_it_received_this_score,
        "reasons_to_proceed": candidate.reasons_to_proceed,
        "reasons_not_to_proceed": candidate.reasons_not_to_proceed,
        "blockers": [blocker.model_dump(mode="json") for blocker in candidate.blockers],
        "dependencies": dependency_ids,
        "uncertainty": candidate.uncertainty,
        "source_finding_ids": candidate.source_finding_ids,
        "source_comparison_ids": candidate.source_comparison_ids,
        "source_snapshot_ids": candidate.source_snapshot_ids,
        "evidence_fingerprints": candidate.evidence_fingerprints,
        "evidence_freshness": candidate.evidence_freshness,
        "evidence_references": [item.model_dump(mode="json") for item in candidate.evidence_references],
        "semantic_fingerprint": candidate.semantic_key,
        "content_fingerprint": content_fingerprint,
        "provenance_reference": health.provenance_reference if health is not None else None,
    }


def _recommendation_id(semantic_key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"gaia:recommendation:{semantic_key}:{RECOMMENDATION_POLICY_VERSION}"))


def _semantic_key(project_id: str, recommendation_type: str, issue_key: str) -> str:
    return _sha256_json(
        {
            "policy_version": RECOMMENDATION_POLICY_VERSION,
            "project_id": project_id,
            "recommendation_type": recommendation_type,
            "issue_key": issue_key,
        }
    )


def _sha256_json(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _queue_sort_key(recommendation: ProjectRecommendation) -> tuple[int, int, int, str]:
    return (
        _STATE_ORDER.get(recommendation.lifecycle_state, 99),
        _PRIORITY_ORDER.get(recommendation.priority_tier, 99),
        -recommendation.deterministic_score,
        recommendation.recommendation_id,
    )


def _project_sensitivity_weight(project: ProjectConfig) -> int:
    return {
        "public": 16,
        "confidential": 12,
        "restricted": 10,
        "internal": 6,
        "sandbox": 3,
    }.get(project.sensitivity, 5)


def _confidence_from_findings(findings: list[ProjectChangeFinding], freshness: str) -> RecommendationConfidence:
    if freshness == "stale":
        return "medium" if findings else "low"
    if findings:
        return "high"
    return "medium"


def _confidence_from_health(health: ProjectHealthSnapshot) -> RecommendationConfidence:
    return "high" if health.normalized_status in {"blocked", "attention"} else "medium"


def _freshness_score_for_candidate(recommendation_type: str, freshness: str) -> int:
    if recommendation_type == "refresh_project_evidence_before_relying_on_state":
        return {"stale": 15, "aging": 10, "fresh": 0, "unknown": 0}.get(freshness, 0)
    return _FRESHNESS_SCORE.get(freshness, 0)


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _deduplicate_candidates(candidates: list[_Candidate]) -> list[_Candidate]:
    unique: dict[str, _Candidate] = {}
    for candidate in candidates:
        unique[candidate.semantic_key] = candidate
    return sorted(unique.values(), key=lambda item: item.semantic_key)


def validate_recommendation_dependencies(recommendations: list[ProjectRecommendation]) -> None:
    by_id = {item.recommendation_id: item for item in recommendations}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(recommendation_id: str) -> None:
        if recommendation_id in visited:
            return
        if recommendation_id in visiting:
            raise ValueError("Recommendation dependency cycle detected")
        visiting.add(recommendation_id)
        recommendation = by_id[recommendation_id]
        for dependency_id in recommendation.dependencies:
            if dependency_id in by_id:
                visit(dependency_id)
        visiting.remove(recommendation_id)
        visited.add(recommendation_id)

    for recommendation_id in sorted(by_id):
        visit(recommendation_id)
