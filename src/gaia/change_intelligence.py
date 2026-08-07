from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from gaia.audit import AuditRecorder
from gaia.config import Settings
from gaia.db import Database
from gaia.models import (
    ChangeClass,
    ChangeComparisonStatus,
    ChangeConfidence,
    ChangeDirection,
    ChangeFindingStatus,
    ChangeSeverity,
    ProjectChangeComparison,
    ProjectChangeFinding,
    ProjectChangePortfolio,
    ProjectChangePortfolioEntry,
    ProjectConfig,
    ProjectHealthEvidenceReference,
    ProjectHealthSnapshot,
    ProjectHealthStatus,
    utc_now,
)

DETECTOR_VERSION = "gaia-v0.9-b2"
SUPPORTED_HEALTH_SCHEMA_VERSION = 1
SUPPORTED_CHANGE_SCHEMA_VERSION = 1
SUPPORTED_UNDERVALUED_CHANGE_CLASSES = {
    "release_drift",
    "contract_drift",
    "documentation_drift",
    "dependency_drift",
    "test_regression",
}
_SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4, "not_evaluated": -1}
_STATUS_ORDER = {"blocked": 0, "attention": 1, "healthy": 2, "unknown": 3}


@dataclass(slots=True)
class _DetectorOutcome:
    finding_type: ChangeClass
    change_class: ChangeClass
    severity: ChangeSeverity
    direction: ChangeDirection
    confidence: ChangeConfidence
    status: ChangeFindingStatus
    reason_codes: list[str]
    explanation: str
    evidence: dict[str, Any]
    evidence_references: list[ProjectHealthEvidenceReference]
    normalized_payload: dict[str, Any]


class ChangeIntelligenceService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        audit: AuditRecorder,
    ) -> None:
        self.settings = settings
        self.database = database
        self.audit = audit

    def get_project(self, project_id: str) -> ProjectConfig:
        try:
            return self.settings.projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def compare_snapshots(
        self,
        previous_snapshot_id: str,
        current_snapshot_id: str,
    ) -> ProjectChangeComparison:
        previous = self._get_health_snapshot(previous_snapshot_id)
        current = self._get_health_snapshot(current_snapshot_id)
        if previous.project_id != current.project_id:
            raise ValueError("Cross-project snapshot comparison is not allowed")
        self._validate_health_schema(previous)
        self._validate_health_schema(current)
        return self._build_comparison(previous, current)

    def compare_latest_project_health(self, project_id: str) -> ProjectChangeComparison | None:
        self.get_project(project_id)
        snapshots = self.database.list_project_health_snapshots(project_id)
        if len(snapshots) < 2:
            return None
        return self.compare_snapshots(snapshots[1].snapshot_id, snapshots[0].snapshot_id)

    def get_change_comparison(self, comparison_id: str) -> ProjectChangeComparison | None:
        comparison = self.database.get_project_change_comparison(comparison_id)
        if comparison is not None:
            self._validate_change_schema(comparison)
        return comparison

    def list_project_change_comparisons(self, project_id: str) -> list[ProjectChangeComparison]:
        self.get_project(project_id)
        comparisons = self.database.list_project_change_comparisons(project_id)
        for comparison in comparisons:
            self._validate_change_schema(comparison)
        return comparisons

    def list_project_change_findings(self, project_id: str) -> list[ProjectChangeFinding]:
        self.get_project(project_id)
        findings = self.database.list_project_change_findings(project_id)
        for finding in findings:
            self._validate_finding_schema(finding)
        return findings

    def latest_project_change_findings(self, project_id: str) -> list[ProjectChangeFinding]:
        self.get_project(project_id)
        findings = self.database.latest_project_change_findings(project_id)
        for finding in findings:
            self._validate_finding_schema(finding)
        return findings

    def recent_project_change_findings(self, limit: int = 50) -> list[ProjectChangeFinding]:
        project_ids = sorted(project.project_id for project in self.settings.projects.values() if project.enabled)
        findings = self.database.recent_project_change_findings(project_ids, limit=limit)
        for finding in findings:
            self._validate_finding_schema(finding)
        return findings

    def portfolio_change_view(self) -> ProjectChangePortfolio:
        entries: list[ProjectChangePortfolioEntry] = []
        overall_counts: Counter[str] = Counter()
        class_counts: Counter[str] = Counter()
        for project in sorted(self.settings.projects.values(), key=lambda item: item.project_id):
            if not project.enabled:
                continue
            latest_health = self.database.latest_project_health_snapshot(project.project_id)
            latest_findings = self.latest_project_change_findings(project.project_id)
            latest_comparison = self._latest_meaningful_comparison(project.project_id)
            counts_by_severity = Counter(finding.severity for finding in latest_findings)
            for severity, count in counts_by_severity.items():
                overall_counts[severity] += count
            for finding in latest_findings:
                class_counts[finding.change_class] += 1
            entries.append(
                ProjectChangePortfolioEntry(
                    project_id=project.project_id,
                    project_name=project.name,
                    latest_health_status=latest_health.normalized_status if latest_health else "unknown",
                    latest_meaningful_change_timestamp=(
                        latest_comparison.capture_timestamp if latest_comparison else None
                    ),
                    latest_comparison_id=latest_comparison.comparison_id if latest_comparison else None,
                    latest_comparison_freshness=_comparison_record_freshness(project, latest_comparison.capture_timestamp)
                    if latest_comparison
                    else "unknown",
                    stale_evidence=(
                        _comparison_record_freshness(project, latest_comparison.capture_timestamp) == "stale"
                        if latest_comparison
                        else False
                    ),
                    counts_by_severity=dict(sorted(counts_by_severity.items(), key=lambda item: _SEVERITY_ORDER.get(item[0], 99))),
                    latest_findings=latest_findings,
                )
            )
        return ProjectChangePortfolio(
            generated_at=utc_now(),
            projects=entries,
            counts_by_severity=dict(sorted(overall_counts.items(), key=lambda item: _SEVERITY_ORDER.get(item[0], 99))),
            counts_by_change_class=dict(sorted(class_counts.items())),
        )

    def _build_comparison(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> ProjectChangeComparison:
        comparison_key = self._comparison_key(previous, current)
        existing = self.database.get_project_change_comparison(comparison_key["comparison_id"])
        if existing is not None:
            return existing

        if previous.content_fingerprint == current.content_fingerprint:
            comparison_status: ChangeComparisonStatus = "no_meaningful_change"
        else:
            comparison_status = "compared"

        outcomes = self._evaluate_detectors(previous, current)
        findings = [
            self._build_finding(previous, current, outcome, comparison_key["comparison_id"])
            for outcome in outcomes
            if outcome.status == "active"
        ]
        findings.sort(key=lambda item: (_SEVERITY_ORDER.get(item.severity, 99), item.change_class, item.finding_id))

        meaningful = bool(findings)
        if not meaningful and previous.content_fingerprint != current.content_fingerprint:
            outcomes.append(
                _DetectorOutcome(
                    finding_type="snapshot_delta",
                    change_class="snapshot_delta",
                    severity="info",
                    direction=_direction_from_transition(previous.normalized_status, current.normalized_status),
                    confidence=self._comparison_confidence(previous, current),
                    status="active",
                    reason_codes=["snapshot_delta"],
                    explanation="The normalized project-state fingerprint changed.",
                    evidence=self._comparison_evidence(previous, current),
                    evidence_references=self._comparison_evidence_references(previous, current),
                    normalized_payload={
                        "before_fingerprint": previous.content_fingerprint,
                        "after_fingerprint": current.content_fingerprint,
                    },
                )
            )
            findings = [
                self._build_finding(previous, current, outcomes[-1], comparison_key["comparison_id"])
            ]
            meaningful = True

        detector_outcomes = [self._outcome_payload(outcome) for outcome in outcomes]
        comparison = ProjectChangeComparison(
            comparison_id=comparison_key["comparison_id"],
            detector_version=DETECTOR_VERSION,
            project_id=previous.project_id,
            comparison_kind="explicit",
            previous_snapshot_id=previous.snapshot_id,
            current_snapshot_id=current.snapshot_id,
            previous_snapshot_fingerprint=previous.content_fingerprint,
            current_snapshot_fingerprint=current.content_fingerprint,
            capture_timestamp=utc_now(),
            comparison_status="compared" if meaningful else comparison_status,
            meaningful_change_detected=meaningful,
            finding_count=len(findings),
            finding_ids=[finding.finding_id for finding in findings],
            detector_outcomes=detector_outcomes,
            normalized_payload={
                "previous": _comparison_snapshot_payload(previous),
                "current": _comparison_snapshot_payload(current),
                "summary": {
                    "meaningful_change_detected": meaningful,
                    "finding_count": len(findings),
                    "detector_outcomes": detector_outcomes,
                },
            },
            provenance_reference=current.provenance_reference or previous.provenance_reference,
        )
        comparison.content_fingerprint = _comparison_fingerprint(comparison)
        self.database.insert_project_change_comparison(comparison)
        audit_event = self.audit.record(
            category="change_intelligence",
            operation="compare_snapshots",
            project_id=previous.project_id,
            outcome="success",
            metadata={
                "comparison_id": comparison.comparison_id,
                "finding_count": comparison.finding_count,
                "meaningful_change_detected": comparison.meaningful_change_detected,
            },
        )
        comparison.audit_event_id = audit_event.event_id
        self.database.update_project_change_comparison_audit_event(comparison.comparison_id, audit_event.event_id)

        persisted_findings: list[ProjectChangeFinding] = []
        for finding in findings:
            finding.audit_event_id = self.audit.record(
                category="change_intelligence",
                operation="detect_finding",
                project_id=previous.project_id,
                outcome="success",
                metadata={
                    "comparison_id": comparison.comparison_id,
                    "finding_id": finding.finding_id,
                    "change_class": finding.change_class,
                },
            ).event_id
            self.database.insert_project_change_finding(finding)
            self.database.update_project_change_finding_audit_event(finding.finding_id, finding.audit_event_id)
            persisted_findings.append(finding)
        comparison.finding_ids = [finding.finding_id for finding in persisted_findings]
        comparison.finding_count = len(persisted_findings)
        return comparison

    def _evaluate_detectors(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        outcomes: list[_DetectorOutcome] = []
        outcomes.extend(self._detect_health_transition(previous, current))
        outcomes.extend(self._detect_branch_and_head(previous, current))
        outcomes.extend(self._detect_working_tree(previous, current))
        outcomes.extend(self._detect_upstream(previous, current))
        outcomes.extend(self._detect_important_paths(previous, current))
        outcomes.extend(self._detect_freshness(previous, current))
        outcomes.extend(self._detect_configuration(previous, current))
        outcomes.extend(self._not_evaluated_outcomes(previous, current))
        return outcomes

    def _detect_health_transition(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        if previous.normalized_status == current.normalized_status:
            return []
        direction = _direction_from_health(previous.normalized_status, current.normalized_status)
        severity = _health_transition_severity(previous.normalized_status, current.normalized_status)
        confidence = _confidence_from_snapshot_pair(previous, current)
        reason_codes = ["health_transition", f"{previous.normalized_status}_to_{current.normalized_status}"]
        evidence = {
            "before": previous.normalized_status,
            "after": current.normalized_status,
            "reason_codes_removed": _ordered_difference(previous.reason_codes, current.reason_codes),
            "reason_codes_added": _ordered_difference(current.reason_codes, previous.reason_codes),
        }
        explanation = (
            f"Project health changed from {previous.normalized_status} to {current.normalized_status}."
        )
        return [
            _DetectorOutcome(
                finding_type="health_transition",
                change_class="health_transition",
                severity=severity,
                direction=direction,
                confidence=confidence,
                status="active",
                reason_codes=reason_codes,
                explanation=explanation,
                evidence=evidence,
                evidence_references=self._comparison_evidence_references(previous, current),
                normalized_payload=evidence,
            )
        ]

    def _detect_branch_and_head(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        before = _git_state(previous)
        after = _git_state(current)
        outcomes: list[_DetectorOutcome] = []
        if before.get("branch") != after.get("branch") or before.get("detached_head") != after.get("detached_head"):
            direction: ChangeDirection = "changed"
            if before.get("detached_head") is False and after.get("detached_head") is True:
                direction = "degraded"
            elif before.get("detached_head") is True and after.get("detached_head") is False:
                direction = "improved"
            severity: ChangeSeverity = "medium" if direction == "degraded" else "info"
            outcomes.append(
                _DetectorOutcome(
                    finding_type="branch_change",
                    change_class="branch_change",
                    severity=severity,
                    direction=direction,
                    confidence=_confidence_from_snapshot_pair(previous, current),
                    status="active",
                    reason_codes=["branch_change"],
                    explanation=_explain_change("branch", before.get("branch"), after.get("branch")),
                    evidence={"before": before.get("branch"), "after": after.get("branch"), "detached_before": before.get("detached_head"), "detached_after": after.get("detached_head")},
                    evidence_references=self._comparison_evidence_references(previous, current),
                    normalized_payload={"before": before.get("branch"), "after": after.get("branch")},
                )
        )
        if before.get("commit_sha") != after.get("commit_sha"):
            head_severity: ChangeSeverity = "info"
            if current.normalized_status in {"attention", "blocked"}:
                head_severity = "medium"
            outcomes.append(
                _DetectorOutcome(
                    finding_type="head_change",
                    change_class="head_change",
                    severity=head_severity,
                    direction="changed",
                    confidence=_confidence_from_snapshot_pair(previous, current),
                    status="active",
                    reason_codes=["head_change"],
                    explanation=_explain_change("HEAD", before.get("commit_sha"), after.get("commit_sha")),
                    evidence={"before": before.get("commit_sha"), "after": after.get("commit_sha")},
                    evidence_references=self._comparison_evidence_references(previous, current),
                    normalized_payload={"before": before.get("commit_sha"), "after": after.get("commit_sha")},
                )
            )
        return outcomes

    def _detect_working_tree(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        before = _git_state(previous)
        after = _git_state(current)
        before_state = "clean" if before.get("is_clean") else "dirty"
        after_state = "clean" if after.get("is_clean") else "dirty"
        if before_state == after_state and before.get("tracked_modifications_count") == after.get("tracked_modifications_count") and before.get("untracked_item_count") == after.get("untracked_item_count"):
            return []
        direction = _direction_from_cleanliness(before_state, after_state)
        severity = _working_tree_severity(before_state, after_state, before, after)
        evidence = {
            "before_state": before_state,
            "after_state": after_state,
            "tracked_modifications_before": before.get("tracked_modifications_count"),
            "tracked_modifications_after": after.get("tracked_modifications_count"),
            "untracked_count_before": before.get("untracked_item_count"),
            "untracked_count_after": after.get("untracked_item_count"),
        }
        explanation = "Working-tree cleanliness changed."
        return [
            _DetectorOutcome(
                finding_type="working_tree_change",
                change_class="working_tree_change",
                severity=severity,
                direction=direction,
                confidence=_confidence_from_snapshot_pair(previous, current),
                status="active",
                reason_codes=["working_tree_change"],
                explanation=explanation,
                evidence=evidence,
                evidence_references=self._comparison_evidence_references(previous, current),
                normalized_payload=evidence,
            )
        ]

    def _detect_upstream(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        before = _git_state(previous)
        after = _git_state(current)
        if (
            before.get("upstream_name") == after.get("upstream_name")
            and before.get("ahead") == after.get("ahead")
            and before.get("behind") == after.get("behind")
        ):
            return []
        direction: ChangeDirection = "changed"
        severity = _upstream_severity(before, after)
        evidence = {
            "before_upstream": before.get("upstream_name"),
            "after_upstream": after.get("upstream_name"),
            "ahead_before": before.get("ahead"),
            "ahead_after": after.get("ahead"),
            "behind_before": before.get("behind"),
            "behind_after": after.get("behind"),
        }
        explanation = "Upstream divergence changed."
        if before.get("upstream_name") is None and after.get("upstream_name") is not None:
            direction = "improved"
            explanation = "An upstream branch became available."
        elif before.get("upstream_name") is not None and after.get("upstream_name") is None:
            direction = "degraded"
            explanation = "The upstream branch disappeared."
        return [
            _DetectorOutcome(
                finding_type="upstream_divergence",
                change_class="upstream_divergence",
                severity=severity,
                direction=direction,
                confidence=_confidence_from_snapshot_pair(previous, current),
                status="active",
                reason_codes=["upstream_divergence"],
                explanation=explanation,
                evidence=evidence,
                evidence_references=self._comparison_evidence_references(previous, current),
                normalized_payload=evidence,
            )
        ]

    def _detect_important_paths(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        before = _configured_evidence(previous)
        after = _configured_evidence(current)
        before_present = dict(before.get("required_paths_present", {}))
        after_present = dict(after.get("required_paths_present", {}))
        if before_present == after_present:
            return []
        evidence = {
            "before": before_present,
            "after": after_present,
            "missing_before": list(before.get("missing_important_paths", [])),
            "missing_after": list(after.get("missing_important_paths", [])),
        }
        added = [path for path, present in after_present.items() if present and not before_present.get(path, False)]
        removed = [path for path, present in before_present.items() if present and not after_present.get(path, False)]
        direction: ChangeDirection = "changed"
        severity: ChangeSeverity = "medium" if removed else "info"
        if removed and not added:
            direction = "degraded"
        elif added and not removed:
            direction = "improved"
        explanation = "Configured important-path presence changed."
        return [
            _DetectorOutcome(
                finding_type="important_path_change",
                change_class="important_path_change",
                severity=severity,
                direction=direction,
                confidence=_confidence_from_snapshot_pair(previous, current),
                status="active",
                reason_codes=["important_path_change"],
                explanation=explanation,
                evidence=evidence,
                evidence_references=self._comparison_evidence_references(previous, current),
                normalized_payload=evidence,
            )
        ]

    def _detect_freshness(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        before_state = _comparison_freshness_state(previous)
        after_state = _comparison_freshness_state(current)
        if before_state == after_state:
            return []
        direction = _direction_from_freshness(before_state, after_state)
        severity = _freshness_severity(before_state, after_state)
        evidence = {"before": before_state, "after": after_state}
        explanation = "Evidence freshness changed."
        return [
            _DetectorOutcome(
                finding_type="evidence_freshness_change",
                change_class="evidence_freshness_change",
                severity=severity,
                direction=direction,
                confidence=_confidence_from_snapshot_pair(previous, current),
                status="active",
                reason_codes=["evidence_freshness_change"],
                explanation=explanation,
                evidence=evidence,
                evidence_references=self._comparison_evidence_references(previous, current),
                normalized_payload=evidence,
            )
        ]

    def _detect_configuration(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        if previous.project_configuration_fingerprint == current.project_configuration_fingerprint:
            return []
        direction: ChangeDirection = "changed"
        severity: ChangeSeverity = "medium"
        if current.normalized_status == "blocked":
            severity = "high"
        explanation = "Project configuration fingerprint changed."
        evidence = {
            "before": previous.project_configuration_fingerprint,
            "after": current.project_configuration_fingerprint,
        }
        return [
            _DetectorOutcome(
                finding_type="configuration_change",
                change_class="configuration_change",
                severity=severity,
                direction=direction,
                confidence="high",
                status="active",
                reason_codes=["configuration_change"],
                explanation=explanation,
                evidence=evidence,
                evidence_references=self._comparison_evidence_references(previous, current),
                normalized_payload=evidence,
            )
        ]

    def _not_evaluated_outcomes(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[_DetectorOutcome]:
        evidence = {
            "reason": "No reliable structured source exists in B2 for this detector.",
            "snapshot_ids": [previous.snapshot_id, current.snapshot_id],
        }
        return [
            _DetectorOutcome(
                finding_type="not_evaluated",
                change_class=change_class,  # type: ignore[arg-type]
                severity="not_evaluated",
                direction="unknown",
                confidence="unknown",
                status="not_evaluated",
                reason_codes=["not_evaluated"],
                explanation="Detector not evaluated in B2.",
                evidence=evidence,
                evidence_references=self._comparison_evidence_references(previous, current),
                normalized_payload={"change_class": change_class, "status": "not_evaluated"},
            )
            for change_class in sorted(SUPPORTED_UNDERVALUED_CHANGE_CLASSES)
        ]

    def _build_finding(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
        outcome: _DetectorOutcome,
        comparison_id: str,
    ) -> ProjectChangeFinding:
        normalized_payload = {
            "previous_snapshot_fingerprint": previous.content_fingerprint,
            "current_snapshot_fingerprint": current.content_fingerprint,
            "project_id": previous.project_id,
            "finding_type": outcome.finding_type,
            "change_class": outcome.change_class,
            "severity": outcome.severity,
            "direction": outcome.direction,
            "confidence": outcome.confidence,
            "reason_codes": outcome.reason_codes,
            "explanation": outcome.explanation,
            "evidence": outcome.evidence,
            "status": outcome.status,
            "detector_version": DETECTOR_VERSION,
        }
        finding = ProjectChangeFinding(
            finding_id=_deterministic_uuid("finding", normalized_payload),
            comparison_id=comparison_id,
            project_id=previous.project_id,
            finding_type=outcome.finding_type,
            change_class=outcome.change_class,
            severity=outcome.severity,
            direction=outcome.direction,
            confidence=outcome.confidence,
            status=outcome.status,
            previous_snapshot_id=previous.snapshot_id,
            current_snapshot_id=current.snapshot_id,
            previous_snapshot_fingerprint=previous.content_fingerprint,
            current_snapshot_fingerprint=current.content_fingerprint,
            reason_codes=outcome.reason_codes,
            explanation=outcome.explanation,
            evidence_references=outcome.evidence_references,
            evidence=outcome.evidence,
            normalized_payload=normalized_payload,
            detector_version=DETECTOR_VERSION,
        )
        finding.content_fingerprint = _finding_fingerprint(finding)
        return finding

    def _get_health_snapshot(self, snapshot_id: str) -> ProjectHealthSnapshot:
        snapshot = self.database.get_project_health_snapshot(snapshot_id)
        if snapshot is None:
            raise KeyError(f"Unknown project health snapshot: {snapshot_id}")
        return snapshot

    def _validate_health_schema(self, snapshot: ProjectHealthSnapshot) -> None:
        if snapshot.schema_version != SUPPORTED_HEALTH_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported project-health schema version: {snapshot.schema_version}"
            )

    def _validate_change_schema(self, comparison: ProjectChangeComparison) -> None:
        if comparison.schema_version != SUPPORTED_CHANGE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported project-change schema version: {comparison.schema_version}"
            )

    def _validate_finding_schema(self, finding: ProjectChangeFinding) -> None:
        if finding.schema_version != SUPPORTED_CHANGE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported project-change schema version: {finding.schema_version}"
            )

    def _latest_meaningful_comparison(self, project_id: str) -> ProjectChangeComparison | None:
        comparisons = self.database.list_project_change_comparisons(project_id)
        for comparison in comparisons:
            if comparison.meaningful_change_detected:
                return comparison
        return None

    def _comparison_evidence(self, previous: ProjectHealthSnapshot, current: ProjectHealthSnapshot) -> dict[str, Any]:
        return {
            "before_status": previous.normalized_status,
            "after_status": current.normalized_status,
            "before_fingerprint": previous.content_fingerprint,
            "after_fingerprint": current.content_fingerprint,
        }

    def _comparison_evidence_references(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> list[ProjectHealthEvidenceReference]:
        return [
            ProjectHealthEvidenceReference(
                evidence_kind="project_health_snapshot",
                evidence_id=previous.snapshot_id,
                description="Previous project-health snapshot",
                freshness="captured",
                details={"status": previous.normalized_status, "fingerprint": previous.content_fingerprint},
            ),
            ProjectHealthEvidenceReference(
                evidence_kind="project_health_snapshot",
                evidence_id=current.snapshot_id,
                description="Current project-health snapshot",
                freshness="captured",
                details={"status": current.normalized_status, "fingerprint": current.content_fingerprint},
            ),
        ]

    def _comparison_key(self, previous: ProjectHealthSnapshot, current: ProjectHealthSnapshot) -> dict[str, str]:
        payload = {
            "detector_version": DETECTOR_VERSION,
            "project_id": previous.project_id,
            "previous_snapshot_fingerprint": previous.content_fingerprint,
            "current_snapshot_fingerprint": current.content_fingerprint,
        }
        comparison_id = _deterministic_uuid("comparison", payload)
        return {"comparison_id": comparison_id, "payload": json.dumps(payload, sort_keys=True, separators=(",", ":"))}

    def _comparison_confidence(
        self,
        previous: ProjectHealthSnapshot,
        current: ProjectHealthSnapshot,
    ) -> ChangeConfidence:
        if _comparison_freshness_state(previous) == "unknown" or _comparison_freshness_state(current) == "unknown":
            return "medium"
        return "high"

    def _outcome_payload(self, outcome: _DetectorOutcome) -> dict[str, Any]:
        return {
            "finding_type": outcome.finding_type,
            "change_class": outcome.change_class,
            "severity": outcome.severity,
            "direction": outcome.direction,
            "confidence": outcome.confidence,
            "status": outcome.status,
            "reason_codes": outcome.reason_codes,
            "explanation": outcome.explanation,
        }


def _git_state(snapshot: ProjectHealthSnapshot) -> dict[str, Any]:
    return dict(snapshot.normalized_payload.get("git_state", {}))


def _configured_evidence(snapshot: ProjectHealthSnapshot) -> dict[str, Any]:
    return dict(snapshot.normalized_payload.get("configured_evidence", {}))


def _comparison_snapshot_payload(snapshot: ProjectHealthSnapshot) -> dict[str, Any]:
    git_state = _git_state(snapshot)
    evidence = _configured_evidence(snapshot)
    return {
        "snapshot_id": snapshot.snapshot_id,
        "project_id": snapshot.project_id,
        "project_configuration_fingerprint": snapshot.project_configuration_fingerprint,
        "normalized_status": snapshot.normalized_status,
        "reason_codes": list(snapshot.reason_codes),
        "git_state": {
            "branch": git_state.get("branch"),
            "detached_head": git_state.get("detached_head"),
            "commit_sha": git_state.get("commit_sha"),
            "upstream_name": git_state.get("upstream_name"),
            "ahead": git_state.get("ahead"),
            "behind": git_state.get("behind"),
            "is_clean": git_state.get("is_clean"),
            "tracked_modifications_count": git_state.get("tracked_modifications_count"),
            "untracked_item_count": git_state.get("untracked_item_count"),
        },
        "configured_evidence": {
            "required_paths_present": evidence.get("required_paths_present", {}),
            "missing_important_paths": evidence.get("missing_important_paths", []),
            "evidence_freshness": _comparison_freshness_state(snapshot),
        },
    }


def _comparison_freshness_state(snapshot: ProjectHealthSnapshot) -> str:
    evidence = _configured_evidence(snapshot)
    freshness = dict(evidence.get("evidence_freshness", {}))
    state = str(freshness.get("state", "unknown"))
    if state == "unknown":
        return "unknown"
    age_hours = freshness.get("age_hours")
    threshold_hours = freshness.get("threshold_hours")
    if age_hours is None or threshold_hours is None:
        return "unknown"
    try:
        age_value = float(age_hours)
        threshold_value = float(threshold_hours)
    except (TypeError, ValueError):
        return "unknown"
    if age_value <= threshold_value * 0.5:
        return "fresh"
    if age_value <= threshold_value:
        return "aging"
    return "stale"


def _comparison_record_freshness(project: ProjectConfig, captured_at: datetime) -> str:
    threshold_hours = int(project.health_rules.get("evidence_freshness_hours", 24))
    age = utc_now() - captured_at
    age_hours = age.total_seconds() / 3600
    if age_hours <= threshold_hours * 0.5:
        return "fresh"
    if age_hours <= threshold_hours:
        return "aging"
    return "stale"


def _comparison_fingerprint(comparison: ProjectChangeComparison) -> str:
    payload = comparison.normalized_payload | {
        "comparison_id": comparison.comparison_id,
        "schema_version": comparison.schema_version,
        "detector_version": comparison.detector_version,
        "project_id": comparison.project_id,
        "previous_snapshot_id": comparison.previous_snapshot_id,
        "current_snapshot_id": comparison.current_snapshot_id,
    }
    return _sha256_json(payload)


def _finding_fingerprint(finding: ProjectChangeFinding) -> str:
    payload = finding.normalized_payload | {
        "schema_version": finding.schema_version,
        "detector_version": finding.detector_version,
        "project_id": finding.project_id,
        "change_class": finding.change_class,
        "severity": finding.severity,
        "direction": finding.direction,
        "confidence": finding.confidence,
    }
    return _sha256_json(payload)


def _sha256_json(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _deterministic_uuid(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return str(uuid5(NAMESPACE_URL, f"gaia:{prefix}:{canonical}"))


def _ordered_difference(left: list[str], right: list[str]) -> list[str]:
    right_set = set(right)
    return [item for item in left if item not in right_set]


def _direction_from_health(before: ProjectHealthStatus, after: ProjectHealthStatus) -> ChangeDirection:
    if before == after:
        return "unchanged"
    if _STATUS_ORDER.get(after, 99) < _STATUS_ORDER.get(before, 99):
        return "degraded"
    if _STATUS_ORDER.get(after, 99) > _STATUS_ORDER.get(before, 99):
        return "improved"
    return "changed"


def _health_transition_severity(before: ProjectHealthStatus, after: ProjectHealthStatus) -> ChangeSeverity:
    if after == "blocked":
        return "high"
    if before == "blocked" and after in {"attention", "healthy"}:
        return "info"
    if before == "healthy" and after == "attention":
        return "medium"
    if after == "attention":
        return "medium"
    if after == "unknown":
        return "low"
    return "info"


def _direction_from_transition(before: str, after: str) -> ChangeDirection:
    if before == after:
        return "unchanged"
    return "changed"


def _direction_from_cleanliness(before: str, after: str) -> ChangeDirection:
    if before == after:
        return "unchanged"
    if before == "clean" and after == "dirty":
        return "degraded"
    if before == "dirty" and after == "clean":
        return "improved"
    return "changed"


def _direction_from_freshness(before: str, after: str) -> ChangeDirection:
    if before == after:
        return "unchanged"
    if _freshness_rank(after) < _freshness_rank(before):
        return "improved"
    if _freshness_rank(after) > _freshness_rank(before):
        return "degraded"
    return "changed"


def _freshness_rank(state: str) -> int:
    return {"unknown": 3, "stale": 2, "aging": 1, "fresh": 0}.get(state, 3)


def _working_tree_severity(
    before_state: str,
    after_state: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> ChangeSeverity:
    if before_state == "clean" and after_state == "dirty":
        return "medium"
    if before_state == "dirty" and after_state == "clean":
        return "info"
    before_total = int(before.get("tracked_modifications_count") or 0) + int(before.get("untracked_item_count") or 0)
    after_total = int(after.get("tracked_modifications_count") or 0) + int(after.get("untracked_item_count") or 0)
    if after_total > before_total:
        return "low"
    if after_total < before_total:
        return "info"
    return "low"


def _upstream_severity(before: dict[str, Any], after: dict[str, Any]) -> ChangeSeverity:
    before_ahead = int(before.get("ahead") or 0)
    after_ahead = int(after.get("ahead") or 0)
    before_behind = int(before.get("behind") or 0)
    after_behind = int(after.get("behind") or 0)
    if before.get("upstream_name") is None and after.get("upstream_name") is not None:
        return "info"
    if before.get("upstream_name") is not None and after.get("upstream_name") is None:
        return "medium"
    if after_behind > before_behind:
        return "medium"
    if after_behind < before_behind:
        return "info"
    if after_ahead > before_ahead:
        return "low"
    if after_ahead < before_ahead:
        return "info"
    return "low"


def _freshness_severity(before: str, after: str) -> ChangeSeverity:
    if before == "fresh" and after == "aging":
        return "low"
    if before == "fresh" and after == "stale":
        return "medium"
    if before == "aging" and after == "stale":
        return "medium"
    if after == "fresh":
        return "info"
    if after == "unknown":
        return "low"
    return "low"


def _confidence_from_snapshot_pair(previous: ProjectHealthSnapshot, current: ProjectHealthSnapshot) -> ChangeConfidence:
    if previous.normalized_payload and current.normalized_payload:
        if _comparison_freshness_state(previous) == "unknown" or _comparison_freshness_state(current) == "unknown":
            return "medium"
        return "high"
    return "unknown"


def _explain_change(label: str, before: Any, after: Any) -> str:
    return f"{label} changed from {before!s} to {after!s}."
