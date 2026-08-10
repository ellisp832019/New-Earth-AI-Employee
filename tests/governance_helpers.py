from __future__ import annotations

from datetime import UTC, datetime

import httpx

from gaia.governance_context import (
    GovernanceBrief,
    GovernanceContext,
    GovernanceFindingContext,
    GovernanceFreshness,
    GovernanceInterpretation,
    GovernancePrioritySummary,
    GovernanceSourceState,
    GovernanceWorkPackagePreview,
    NeosGovernanceFinding,
    NeosGovernanceProjectView,
    NeosGovernanceReport,
    NeosGovernanceSnapshot,
    NeosGovernanceStatus,
)


def sample_governance_context() -> GovernanceContext:
    observed_at = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    snapshot = NeosGovernanceSnapshot(
        snapshot_id="snapshot-001",
        schema_version=1,
        platform_core_governance_version="1.0.0",
        platform_core_governance_hash="pc-hash",
        platform_core_merge_commit="pc-merge",
        neos_version="1.0.0",
        neos_commit="neos-commit",
        observed_at=observed_at,
        readiness="READY",
        status_counts={"ready": 1},
        severity_counts={"ERROR": 1},
        findings=["finding-001"],
        unresolved_unknowns=["unknown dependency state"],
        evidence_references={"docs": ["docs/governance.md"]},
        source_fingerprint="fingerprint-001",
    )
    finding = NeosGovernanceFinding(
        snapshot_id=snapshot.snapshot_id,
        finding_id="finding-001",
        rule_id="NEOS-GOV-001",
        status="ACTIVE",
        severity="ERROR",
        system_id="sample-system",
        project_id="sample",
        canonical_owner="Platform Core",
        recommended_owner="GAIA",
        declared_state={"identity": "canonical"},
        observed_state={"identity": "observed"},
        evidence={"source": ["governance/status"]},
        affected_systems=["sample-system"],
        affected_repositories=["sample-repo"],
        remediation_category="review",
        confidence=0.96,
        explanation="Canonical system existence is confirmed and ready for review.",
        governance_version="1.0.0",
        neos_version="1.0.0",
    )
    report = NeosGovernanceReport(
        schema_version=1,
        governance_version="1.0.0",
        platform_core={"status": "AVAILABLE"},
        observed={"estate": "sample"},
        declared={"estate": "sample"},
        systems=[{"system_id": "sample-system"}],
        findings=[finding],
        summary={"readiness": "READY"},
        observed_at=observed_at,
        source_commit="neos-commit",
        governance_doc={"path": "registry/governance.yaml"},
        snapshot=snapshot,
    )
    status = NeosGovernanceStatus(
        schema_version=1,
        status="READY",
        summary={"readiness": "READY"},
        platform_core={"status": "AVAILABLE"},
        observed={"estate": "sample"},
        declared={"estate": "sample"},
        snapshot=snapshot,
        governance_version="1.0.0",
        neos_version="1.0.0",
    )
    project = NeosGovernanceProjectView(
        schema_version=1,
        status="READY",
        project_id="sample",
        system={"system_id": "sample-system", "project_id": "sample"},
        findings=[finding],
        platform_core={"status": "AVAILABLE"},
        snapshot=snapshot,
        observed={"estate": "sample"},
        governance_version="1.0.0",
        neos_version="1.0.0",
    )
    source = GovernanceSourceState(
        base_url="http://127.0.0.1:8765",
        available=True,
        compatibility_state="compatible",
        status=status,
        report=report,
        project=project,
        snapshot=snapshot,
        findings=[finding],
        received_at=observed_at,
        source_timestamp=observed_at,
        governance_version="1.0.0",
        neos_version="1.0.0",
        snapshot_id=snapshot.snapshot_id,
        source_hash="source-hash-001",
        cache_state="fresh",
    )
    interpretation = GovernanceInterpretation(
        summary="NEOS reports one active governance finding.",
        explanation="The observed estate contains one active governance finding that requires review.",
        review_questions=[
            "Is the canonical system registered?",
            "Does the observed repository still match the declared identity?",
        ],
        recommended_next_actions=[
            "Review the active governance finding.",
            "Preserve UNKNOWN where the source does not provide certainty.",
        ],
    )
    priority = GovernancePrioritySummary(
        operational_priority="P1",
        deterministic_score=91,
        ranked_finding_ids=["finding-001"],
        ranking_basis=["severity=ERROR:80", "critical_rule:+6", "project_match:+8"],
    )
    work_package = GovernanceWorkPackagePreview(
        source_finding_id="finding-001",
        rule_id="NEOS-GOV-001",
        snapshot_id=snapshot.snapshot_id,
        source_severity="ERROR",
        operational_priority="P1",
        canonical_owner="Platform Core",
        recommended_owner="GAIA",
        declared_state=finding.declared_state,
        observed_state=finding.observed_state,
        evidence=finding.evidence,
        proposed_tasks=["Review the registered canonical system.", "Compare declared and observed identity."],
        review_questions=["Is the source record current?", "Should the finding remain active?"],
        safety_boundary=["read-only NEOS source", "no automatic remediation", "human review required"],
        codex_prompt="DRAFT - NOT EXECUTED\n\nReview the governance finding without mutating the source.",
        auto_execute=False,
    )
    brief = GovernanceBrief(
        estate_status="READY",
        snapshot_id=snapshot.snapshot_id,
        headline="Governance context ready.",
        facts=["Estate readiness: READY", "Snapshot ID: snapshot-001", "Findings: 1"],
        unknowns=["Source timestamp missing."],
        programme_impact=["Programme roadmap context available."],
        recommended_human_reviews=["NEOS-GOV-001: P1 - The observed estate contains one active governance finding that requires review."],
        markdown=(
            "# Architecture Governance\n\n"
            "Estate readiness: READY\n\n"
            "Snapshot:\n- Snapshot ID: snapshot-001\n- Findings: 1\n\n"
            "Top findings:\n- NEOS-GOV-001: P1 - The observed estate contains one active governance finding that requires review.\n"
        ),
    )
    return GovernanceContext(
        source=source,
        interpretation=interpretation,
        priority=priority,
        programme_context={"downstream_only": True, "finding_count": 1},
        recommended_actions=["Review the active governance finding."],
        work_package=work_package,
        freshness=GovernanceFreshness(
            received_at=observed_at,
            source_timestamp=observed_at,
            age_seconds=0.0,
            state="fresh",
            notes=["Fresh governance snapshot."],
        ),
        limitations=["Source timestamp unavailable."],
        findings=[
            GovernanceFindingContext(
                source=finding,
                interpretation=interpretation,
                priority=priority,
                work_package_preview=work_package,
            )
        ],
        brief=brief,
    )


class FakeGovernanceContextService:
    def __init__(self, context: GovernanceContext | None = None) -> None:
        self.context_value = context or sample_governance_context()

    def context(self, project_id: str | None = None, finding_id: str | None = None) -> GovernanceContext:
        return self.context_value

    def brief(self, project_id: str | None = None) -> GovernanceBrief:
        if self.context_value.brief is None:
            raise KeyError("Governance brief unavailable")
        return self.context_value.brief

    def work_package_preview(self, finding_id: str, *, project_id: str | None = None) -> GovernanceWorkPackagePreview:
        if self.context_value.work_package is None:
            raise KeyError(f"Unknown governance finding: {finding_id}")
        return self.context_value.work_package

    def close(self) -> None:
        return None


def governance_transport() -> httpx.MockTransport:
    payloads = _governance_payloads()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/governance":
            return httpx.Response(200, json=payloads["report"])
        if path == "/governance/status":
            return httpx.Response(200, json=payloads["status"])
        if path == "/governance/findings":
            return httpx.Response(200, json={"findings": payloads["report"]["findings"]})
        if path == "/governance/project/sample":
            return httpx.Response(200, json=payloads["project"])
        if path == "/governance/snapshot":
            return httpx.Response(200, json=payloads["snapshot"])
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


def _governance_payloads() -> dict[str, dict[str, object]]:
    context = sample_governance_context()
    return {
        "report": context.source.report.model_dump(mode="json") if context.source.report else {},
        "status": context.source.status.model_dump(mode="json") if context.source.status else {},
        "project": context.source.project.model_dump(mode="json") if context.source.project else {},
        "snapshot": context.source.snapshot.model_dump(mode="json") if context.source.snapshot else {},
    }
