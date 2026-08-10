from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from gaia.db import Database
from gaia.models import utc_now

GOVERNANCE_SCHEMA_VERSION = 1
GOVERNANCE_BASE_URL = "http://127.0.0.1:8765"
GOVERNANCE_TIMEOUT_SECONDS = 3.0
GOVERNANCE_COMPATIBLE_MAJOR_VERSION = "1"
PriorityTier = Literal["P0", "P1", "P2", "P3", "P4"]
CompatibilityState = Literal["compatible", "unavailable", "timeout", "malformed", "schema_mismatch", "version_mismatch", "cached"]


class NeosGovernanceSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    snapshot_id: str
    schema_version: int | None = None
    platform_core_governance_version: str | None = None
    platform_core_governance_hash: str | None = None
    platform_core_merge_commit: str | None = None
    neos_version: str | None = None
    neos_commit: str | None = None
    observed_at: datetime | None = None
    readiness: str = "UNKNOWN"
    status_counts: dict[str, Any] = Field(default_factory=dict)
    severity_counts: dict[str, Any] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)
    unresolved_unknowns: list[str] = Field(default_factory=list)
    evidence_references: dict[str, Any] = Field(default_factory=dict)
    source_fingerprint: str | None = None


class NeosGovernanceFinding(BaseModel):
    model_config = ConfigDict(extra="allow")

    snapshot_id: str | None = None
    finding_id: str
    rule_id: str
    status: str = "UNKNOWN"
    severity: str = "UNKNOWN"
    system_id: str | None = None
    project_id: str | None = None
    canonical_owner: str | None = None
    recommended_owner: str | None = None
    declared_state: dict[str, Any] = Field(default_factory=dict)
    observed_state: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    affected_systems: list[str] = Field(default_factory=list)
    affected_repositories: list[str] = Field(default_factory=list)
    remediation_category: str | None = None
    confidence: float | None = None
    explanation: str | None = None
    governance_version: str | None = None
    neos_version: str | None = None


class NeosGovernanceProjectView(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: int | None = None
    status: str = "UNKNOWN"
    project_id: str
    system: dict[str, Any] | None = None
    findings: list[NeosGovernanceFinding] = Field(default_factory=list)
    platform_core: dict[str, Any] = Field(default_factory=dict)
    snapshot: NeosGovernanceSnapshot | None = None
    observed: dict[str, Any] | None = None
    governance_version: str | None = None
    neos_version: str | None = None


class NeosGovernanceStatus(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: int | None = None
    status: str = "UNKNOWN"
    summary: dict[str, Any] = Field(default_factory=dict)
    platform_core: dict[str, Any] = Field(default_factory=dict)
    observed: dict[str, Any] = Field(default_factory=dict)
    declared: dict[str, Any] = Field(default_factory=dict)
    snapshot: NeosGovernanceSnapshot | None = None
    governance_version: str | None = None
    neos_version: str | None = None


class NeosGovernanceReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: int | None = None
    governance_version: str | None = None
    platform_core: dict[str, Any] = Field(default_factory=dict)
    observed: dict[str, Any] = Field(default_factory=dict)
    declared: dict[str, Any] = Field(default_factory=dict)
    systems: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[NeosGovernanceFinding] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime | None = None
    source_commit: str | None = None
    governance_doc: dict[str, Any] = Field(default_factory=dict)
    snapshot: NeosGovernanceSnapshot | None = None


class GovernanceCacheRecord(BaseModel):
    cache_id: str = Field(default_factory=lambda: str(uuid4()))
    source_url: str
    project_id: str | None = None
    finding_id: str | None = None
    received_at: datetime = Field(default_factory=utc_now)
    source_timestamp: datetime | None = None
    governance_version: str | None = None
    neos_version: str | None = None
    snapshot_id: str | None = None
    source_hash: str | None = None
    compatibility_state: CompatibilityState = "compatible"
    payload_json: dict[str, Any] = Field(default_factory=dict)


class GovernanceSourceState(BaseModel):
    model_config = ConfigDict(extra="allow")

    base_url: str
    available: bool = False
    compatibility_state: CompatibilityState = "unavailable"
    status: NeosGovernanceStatus | None = None
    report: NeosGovernanceReport | None = None
    project: NeosGovernanceProjectView | None = None
    snapshot: NeosGovernanceSnapshot | None = None
    findings: list[NeosGovernanceFinding] = Field(default_factory=list)
    received_at: datetime = Field(default_factory=utc_now)
    source_timestamp: datetime | None = None
    governance_version: str | None = None
    neos_version: str | None = None
    snapshot_id: str | None = None
    source_hash: str | None = None
    cache_state: Literal["none", "fresh", "stale"] = "none"
    error: str | None = None


class GovernancePrioritySummary(BaseModel):
    operational_priority: PriorityTier = "P4"
    deterministic_score: int = 0
    ranked_finding_ids: list[str] = Field(default_factory=list)
    ranking_basis: list[str] = Field(default_factory=list)


class GovernanceInterpretation(BaseModel):
    summary: str
    explanation: str
    review_questions: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)


class GovernanceFreshness(BaseModel):
    received_at: datetime = Field(default_factory=utc_now)
    source_timestamp: datetime | None = None
    age_seconds: float | None = None
    state: Literal["fresh", "stale", "unknown"] = "unknown"
    notes: list[str] = Field(default_factory=list)


class GovernanceWorkPackagePreview(BaseModel):
    model_config = ConfigDict(extra="allow")

    preview_id: str = Field(default_factory=lambda: str(uuid4()))
    status: Literal["draft"] = "draft"
    source_finding_id: str
    rule_id: str
    snapshot_id: str | None = None
    source_severity: str = "UNKNOWN"
    operational_priority: PriorityTier = "P4"
    canonical_owner: str | None = None
    recommended_owner: str | None = None
    declared_state: dict[str, Any] = Field(default_factory=dict)
    observed_state: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    proposed_tasks: list[str] = Field(default_factory=list)
    review_questions: list[str] = Field(default_factory=list)
    safety_boundary: list[str] = Field(default_factory=list)
    codex_prompt: str = ""
    auto_execute: bool = False


class GovernanceFindingContext(BaseModel):
    source: NeosGovernanceFinding
    interpretation: GovernanceInterpretation
    priority: GovernancePrioritySummary
    work_package_preview: GovernanceWorkPackagePreview | None = None


class GovernanceBrief(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    estate_status: str = "UNKNOWN"
    snapshot_id: str | None = None
    headline: str = ""
    facts: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    programme_impact: list[str] = Field(default_factory=list)
    recommended_human_reviews: list[str] = Field(default_factory=list)
    markdown: str = ""


class GovernanceContext(BaseModel):
    source: GovernanceSourceState
    interpretation: GovernanceInterpretation
    priority: GovernancePrioritySummary
    programme_context: dict[str, Any] = Field(default_factory=dict)
    recommended_actions: list[str] = Field(default_factory=list)
    work_package: GovernanceWorkPackagePreview | None = None
    freshness: GovernanceFreshness = Field(default_factory=GovernanceFreshness)
    limitations: list[str] = Field(default_factory=list)
    findings: list[GovernanceFindingContext] = Field(default_factory=list)
    brief: GovernanceBrief | None = None


def _major_version(version: str | None) -> str | None:
    if not version:
        return None
    value = str(version).strip()
    if not value:
        return None
    return value.split(".", 1)[0]


def _stable_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class NeosGovernanceClient:
    def __init__(
        self,
        base_url: str = GOVERNANCE_BASE_URL,
        *,
        timeout_seconds: float = GOVERNANCE_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = str(base_url).rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 2.0))
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout, transport=transport, trust_env=False)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NeosGovernanceClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _fetch(self, path: str) -> tuple[dict[str, Any] | None, str | None]:
        try:
            response = self._client.get(path, headers={"accept": "application/json"})
        except httpx.TimeoutException as exc:
            return None, f"timeout:{type(exc).__name__}"
        except httpx.HTTPError as exc:
            return None, f"http_error:{type(exc).__name__}"
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if response.status_code >= 400:
            detail = payload.get("error") if isinstance(payload, dict) else response.text
            return None, f"http_{response.status_code}:{detail or 'error'}"
        if not isinstance(payload, dict):
            return None, "malformed:expected_object"
        return payload, None

    def _parse_model(self, payload: dict[str, Any], model: type[BaseModel]) -> BaseModel:
        parsed = model.model_validate(payload)
        schema_version = payload.get("schema_version")
        if schema_version not in {None, GOVERNANCE_SCHEMA_VERSION, str(GOVERNANCE_SCHEMA_VERSION)}:
            raise ValueError("schema_mismatch")
        version = payload.get("governance_version") or payload.get("neos_version")
        if _major_version(str(version) if version is not None else None) not in {None, GOVERNANCE_COMPATIBLE_MAJOR_VERSION}:
            raise ValueError("version_mismatch")
        return parsed

    def report(self) -> NeosGovernanceReport:
        payload, error = self._fetch("/governance")
        if payload is None:
            return self._unavailable_report(error or "unavailable")
        try:
            parsed = self._parse_model(payload, NeosGovernanceReport)
        except ValueError as exc:
            return self._unavailable_report(str(exc))
        return parsed  # type: ignore[return-value]

    def status(self) -> NeosGovernanceStatus:
        payload, error = self._fetch("/governance/status")
        if payload is None:
            return self._unavailable_status(error or "unavailable")
        try:
            parsed = self._parse_model(payload, NeosGovernanceStatus)
        except ValueError as exc:
            return self._unavailable_status(str(exc))
        return parsed  # type: ignore[return-value]

    def findings(self) -> list[NeosGovernanceFinding]:
        payload, error = self._fetch("/governance/findings")
        if payload is None:
            return []
        findings_payload = payload.get("findings")
        if not isinstance(findings_payload, list):
            return []
        items: list[NeosGovernanceFinding] = []
        for item in findings_payload:
            if isinstance(item, dict):
                try:
                    items.append(self._parse_model(item, NeosGovernanceFinding))  # type: ignore[arg-type]
                except ValueError:
                    continue
        return items

    def project(self, project_id: str) -> NeosGovernanceProjectView:
        payload, error = self._fetch(f"/governance/project/{project_id}")
        if payload is None:
            return self._unavailable_project(project_id, error or "unavailable")
        try:
            parsed = self._parse_model(payload, NeosGovernanceProjectView)
        except ValueError as exc:
            return self._unavailable_project(project_id, str(exc))
        return parsed  # type: ignore[return-value]

    def snapshot(self) -> NeosGovernanceSnapshot:
        payload, error = self._fetch("/governance/snapshot")
        if payload is None:
            return self._unavailable_snapshot(error or "unavailable")
        try:
            parsed = self._parse_model(payload, NeosGovernanceSnapshot)
        except ValueError as exc:
            return self._unavailable_snapshot(str(exc))
        return parsed  # type: ignore[return-value]

    def cache_record(
        self,
        *,
        project_id: str | None,
        finding_id: str | None,
        source: GovernanceSourceState,
    ) -> GovernanceCacheRecord:
        payload = {
            "source": source.model_dump(mode="json"),
            "status": source.status.model_dump(mode="json") if source.status else None,
            "report": source.report.model_dump(mode="json") if source.report else None,
            "project": source.project.model_dump(mode="json") if source.project else None,
            "snapshot": source.snapshot.model_dump(mode="json") if source.snapshot else None,
        }
        return GovernanceCacheRecord(
            source_url=self.base_url,
            project_id=project_id,
            finding_id=finding_id,
            received_at=source.received_at,
            source_timestamp=source.source_timestamp,
            governance_version=source.governance_version,
            neos_version=source.neos_version,
            snapshot_id=source.snapshot_id,
            source_hash=source.source_hash,
            compatibility_state=source.compatibility_state,
            payload_json=payload,
        )

    def _unavailable_report(self, error: str) -> NeosGovernanceReport:
        return NeosGovernanceReport(
            schema_version=GOVERNANCE_SCHEMA_VERSION,
            governance_version="unknown",
            summary={"readiness": "UNKNOWN"},
            platform_core={"status": "UNAVAILABLE", "reason": error},
            observed={"project_count": 0, "projects": []},
            declared={"system_count": 0, "systems": []},
            systems=[],
            findings=[],
            observed_at=utc_now(),
            source_commit=None,
            governance_doc={},
            snapshot=None,
        )

    def _unavailable_status(self, error: str) -> NeosGovernanceStatus:
        return NeosGovernanceStatus(
            schema_version=GOVERNANCE_SCHEMA_VERSION,
            status="UNKNOWN",
            summary={"readiness": "UNKNOWN", "reason": error},
            platform_core={"status": "UNAVAILABLE", "reason": error},
            observed={"project_count": 0, "projects": []},
            declared={"system_count": 0, "systems": []},
            snapshot=None,
            governance_version="unknown",
            neos_version=None,
        )

    def _unavailable_snapshot(self, error: str) -> NeosGovernanceSnapshot:
        return NeosGovernanceSnapshot(
            snapshot_id=f"unavailable-{_stable_hash({'base_url': self.base_url, 'error': error})[:12]}",
            schema_version=GOVERNANCE_SCHEMA_VERSION,
            readiness="UNKNOWN",
            status_counts={},
            severity_counts={},
            findings=[],
            unresolved_unknowns=[],
            evidence_references={"error": error},
            source_fingerprint=None,
        )

    def _unavailable_project(self, project_id: str, error: str) -> NeosGovernanceProjectView:
        return NeosGovernanceProjectView(
            schema_version=GOVERNANCE_SCHEMA_VERSION,
            status="UNKNOWN",
            project_id=project_id,
            system=None,
            findings=[],
            platform_core={"status": "UNAVAILABLE", "reason": error},
            snapshot=None,
            observed=None,
            governance_version="unknown",
            neos_version=None,
        )


class GovernanceContextService:
    def __init__(
        self,
        settings: Any,
        project_service: Any,
        database: Database | None = None,
        *,
        client: NeosGovernanceClient | None = None,
    ) -> None:
        self.settings = settings
        self.project_service = project_service
        self.database = database or getattr(project_service, "database", None)
        self.client = client or NeosGovernanceClient(
            getattr(settings, "neos_base_url", GOVERNANCE_BASE_URL),
            timeout_seconds=float(getattr(settings, "neos_timeout_seconds", GOVERNANCE_TIMEOUT_SECONDS)),
        )

    def close(self) -> None:
        self.client.close()

    def status(self, project_id: str | None = None) -> GovernanceContext:
        return self.context(project_id=project_id)

    def findings(self, project_id: str | None = None) -> GovernanceContext:
        return self.context(project_id=project_id)

    def project(self, project_id: str) -> GovernanceContext:
        return self.context(project_id=project_id)

    def snapshot(self) -> GovernanceContext:
        return self.context()

    def brief(self, project_id: str | None = None) -> GovernanceBrief:
        context = self.context(project_id=project_id)
        return self._brief_from_context(context)

    def work_package_preview(self, finding_id: str, *, project_id: str | None = None) -> GovernanceWorkPackagePreview:
        context = self.context(project_id=project_id, finding_id=finding_id)
        preview = context.work_package
        if preview is not None:
            return preview
        raise KeyError(f"Unknown governance finding: {finding_id}")

    def explain(self, question: str, *, project_id: str | None = None) -> str:
        context = self.context(project_id=project_id)
        lines = [
            "FACT",
            f"- NEOS status: {context.source.status.status if context.source.status else context.source.compatibility_state}",
            f"- Snapshot: {context.source.snapshot.snapshot_id if context.source.snapshot else 'none'}",
            f"- Findings: {len(context.source.findings)}",
            "",
            "INTERPRETATION",
            f"- {context.interpretation.explanation}",
            "",
            "PROPOSAL",
        ]
        for action in context.recommended_actions[:5]:
            lines.append(f"- {action}")
        if not context.recommended_actions:
            lines.append("- Evidence insufficient for a recommendation.")
        if project_id:
            lines.extend(["", f"Project context: {project_id}"])
        return "\n".join(lines).strip()

    def context(self, project_id: str | None = None, finding_id: str | None = None) -> GovernanceContext:
        report = self.client.report()
        status = self.client.status()
        snapshot = report.snapshot or status.snapshot or self.client.snapshot()
        project = self.client.project(project_id) if project_id else None
        findings = list(report.findings)
        if project is not None and project.findings:
            project_keys = {project.project_id}
            if project.system:
                project_keys.update(
                    {
                        str(project.system.get("system_id") or ""),
                        str(project.system.get("project_id") or ""),
                    }
                )
            filtered = [finding for finding in findings if finding.project_id in project_keys or finding.system_id in project_keys]
            findings = filtered or list(project.findings)
        if finding_id is not None:
            selected = next((item for item in findings if item.finding_id == finding_id), None)
            findings = [selected] if selected is not None else []
        source_state = self._source_state(report, status, project, snapshot, findings)
        ranked = self._rank_findings(findings, source_state=source_state, project_id=project_id)
        interpretation, priority, work_package, recommended_actions, limitations = self._interpret(source_state, ranked, project_id=project_id)
        freshness = self._freshness(source_state)
        programme_context = self._programme_context(project_id=project_id, findings=ranked)
        context = GovernanceContext(
            source=source_state,
            interpretation=interpretation,
            priority=priority,
            programme_context=programme_context,
            recommended_actions=recommended_actions,
            work_package=work_package,
            freshness=freshness,
            limitations=limitations,
            findings=ranked,
            brief=None,
        )
        context.brief = self._brief_from_context(context)
        return context

    def _source_state(
        self,
        report: NeosGovernanceReport,
        status: NeosGovernanceStatus,
        project: NeosGovernanceProjectView | None,
        snapshot: NeosGovernanceSnapshot | None,
        findings: list[NeosGovernanceFinding],
    ) -> GovernanceSourceState:
        source_timestamp = snapshot.observed_at if snapshot else None
        governance_version = report.governance_version or status.governance_version or (project.governance_version if project else None)
        neos_version = snapshot.neos_version if snapshot is not None else None
        neos_version = neos_version or status.neos_version or (project.neos_version if project else None)
        source_hash = snapshot.source_fingerprint if snapshot else None
        received_at = utc_now()
        cache_state: Literal["none", "fresh", "stale"] = "none"
        cache_record = self.database.latest_governance_snapshot(self.client.base_url) if self.database is not None else None
        if cache_record is not None:
            age = received_at - cache_record.received_at
            cache_state = "stale" if age > timedelta(hours=24) else "fresh"
        available = status.status != "UNKNOWN" or bool(report.findings) or bool(project and project.findings)
        state = GovernanceSourceState(
            base_url=self.client.base_url,
            available=available,
            compatibility_state="compatible" if available else ("cached" if cache_record is not None else "unavailable"),
            status=status,
            report=report,
            project=project,
            snapshot=snapshot,
            findings=findings,
            received_at=received_at,
            source_timestamp=source_timestamp,
            governance_version=str(governance_version or "unknown"),
            neos_version=str(neos_version) if neos_version is not None else None,
            snapshot_id=snapshot.snapshot_id if snapshot else None,
            source_hash=source_hash,
            cache_state=cache_state,
            error=None,
        )
        if self.database is not None and state.available:
            self.database.insert_governance_snapshot(
                self.client.cache_record(
                    project_id=project.project_id if project else None,
                    finding_id=None,
                    source=state,
                )
            )
        return state

    def _rank_findings(
        self,
        findings: list[NeosGovernanceFinding],
        *,
        source_state: GovernanceSourceState,
        project_id: str | None,
    ) -> list[GovernanceFindingContext]:
        ranked = sorted(
            findings,
            key=lambda finding: self._score_finding(finding, source_state=source_state, project_id=project_id)[1],
            reverse=True,
        )
        contexts: list[GovernanceFindingContext] = []
        for finding in ranked:
            interpretation, priority, preview = self._interpret_finding(finding, source_state=source_state, project_id=project_id)
            contexts.append(
                GovernanceFindingContext(
                    source=finding,
                    interpretation=interpretation,
                    priority=priority,
                    work_package_preview=preview,
                )
            )
        return contexts

    def _score_finding(
        self,
        finding: NeosGovernanceFinding,
        *,
        source_state: GovernanceSourceState,
        project_id: str | None,
    ) -> tuple[PriorityTier, int, list[str]]:
        severity = str(finding.severity or "UNKNOWN").upper()
        base = {"BLOCKER": 95, "ERROR": 80, "WARNING": 60, "INFO": 40, "UNKNOWN": 20}.get(severity, 20)
        basis = [f"severity={severity}:{base}"]
        if finding.status.upper() == "UNKNOWN":
            base -= 5
            basis.append("status=UNKNOWN:-5")
        affected_count = len(finding.affected_systems) + len(finding.affected_repositories)
        if affected_count:
            boost = min(10, affected_count * 2)
            base += boost
            basis.append(f"affected={affected_count}:+{boost}")
        if finding.rule_id in {"NEOS-GOV-001", "NEOS-GOV-002", "NEOS-GOV-008", "NEOS-GOV-009", "NEOS-GOV-012", "NEOS-GOV-013", "NEOS-GOV-014"}:
            base += 6
            basis.append("critical_rule:+6")
        if project_id and finding.project_id and finding.project_id == project_id:
            base += 8
            basis.append("project_match:+8")
        if source_state.project and source_state.project.system:
            project_keys = {
                source_state.project.project_id,
                str(source_state.project.system.get("system_id") or ""),
                str(source_state.project.system.get("project_id") or ""),
            }
            if finding.project_id in project_keys or finding.system_id in project_keys:
                base += 5
                basis.append("source_project_match:+5")
        if source_state.source_hash:
            base += 2
            basis.append("source_hash_present:+2")
        if source_state.cache_state == "stale":
            base -= 4
            basis.append("stale_cache:-4")
        base = max(0, min(100, base))
        tier: PriorityTier = "P4"
        if base >= 90:
            tier = "P0"
        elif base >= 75:
            tier = "P1"
        elif base >= 60:
            tier = "P2"
        elif base >= 40:
            tier = "P3"
        return tier, base, basis

    def _interpret_finding(
        self,
        finding: NeosGovernanceFinding,
        *,
        source_state: GovernanceSourceState,
        project_id: str | None,
    ) -> tuple[GovernanceInterpretation, GovernancePrioritySummary, GovernanceWorkPackagePreview | None]:
        tier, score, basis = self._score_finding(finding, source_state=source_state, project_id=project_id)
        explanation = finding.explanation or (
            f"{finding.rule_id} reports {finding.severity.lower()} for {finding.project_id or finding.system_id or 'unknown'}."
        )
        review_questions = [
            f"What did Platform Core declare for {finding.rule_id}?",
            f"What did NEOS observe for {finding.project_id or finding.system_id or finding.rule_id}?",
            "Is the source fact still current?",
        ]
        if finding.status.upper() == "UNKNOWN":
            review_questions.append("Why is the finding unresolved?")
        proposed_tasks = [
            f"Review NEOS finding {finding.finding_id} for rule {finding.rule_id}.",
            f"Confirm canonical owner {finding.canonical_owner or 'unknown'}.",
        ]
        if finding.affected_repositories:
            proposed_tasks.append(f"Inspect affected repositories: {', '.join(finding.affected_repositories[:3])}.")
        if finding.affected_systems:
            proposed_tasks.append(f"Check impacted systems: {', '.join(finding.affected_systems[:3])}.")
        recommended_actions = [
            f"Review {finding.rule_id} before changing source facts.",
            "Preserve UNKNOWN where the source is ambiguous.",
        ]
        if finding.remediation_category:
            recommended_actions.append(f"Treat remediation as {finding.remediation_category}.")
        preview = GovernanceWorkPackagePreview(
            source_finding_id=finding.finding_id,
            rule_id=finding.rule_id,
            snapshot_id=finding.snapshot_id,
            source_severity=finding.severity,
            operational_priority=tier,
            canonical_owner=finding.canonical_owner,
            recommended_owner=finding.recommended_owner,
            declared_state=finding.declared_state,
            observed_state=finding.observed_state,
            evidence=finding.evidence,
            proposed_tasks=proposed_tasks,
            review_questions=review_questions,
            safety_boundary=[
                "read-only NEOS source",
                "no NEOS mutation",
                "no automatic remediation",
                "human review required",
            ],
            codex_prompt=self._render_codex_prompt(finding, tier, proposed_tasks, review_questions),
            auto_execute=False,
        )
        interpretation = GovernanceInterpretation(
            summary=explanation,
            explanation=explanation,
            review_questions=review_questions,
            recommended_next_actions=recommended_actions,
        )
        priority = GovernancePrioritySummary(
            operational_priority=tier,
            deterministic_score=score,
            ranked_finding_ids=[finding.finding_id],
            ranking_basis=basis,
        )
        return interpretation, priority, preview

    def _interpret(
        self,
        source_state: GovernanceSourceState,
        findings: list[GovernanceFindingContext],
        *,
        project_id: str | None,
    ) -> tuple[GovernanceInterpretation, GovernancePrioritySummary, GovernanceWorkPackagePreview | None, list[str], list[str]]:
        if findings:
            top = findings[0]
            explanation = (
                f"NEOS reports {len(findings)} governance findings. "
                f"Top priority is {top.priority.operational_priority} ({top.source.rule_id})."
            )
            recommended_actions = list(dict.fromkeys(
                [action for item in findings for action in item.interpretation.recommended_next_actions]
            ))
            basis = list(dict.fromkeys([basis for item in findings for basis in item.priority.ranking_basis]))
            priority = GovernancePrioritySummary(
                operational_priority=top.priority.operational_priority,
                deterministic_score=top.priority.deterministic_score,
                ranked_finding_ids=[item.source.finding_id for item in findings],
                ranking_basis=basis,
            )
            interpretation = GovernanceInterpretation(
                summary=top.interpretation.summary,
                explanation=explanation,
                review_questions=top.interpretation.review_questions,
                recommended_next_actions=recommended_actions,
            )
            work_package = top.work_package_preview
        else:
            explanation = "No active governance findings are currently available."
            interpretation = GovernanceInterpretation(
                summary="NEOS reported no governance findings.",
                explanation=explanation,
                review_questions=[
                    "Is the NEOS endpoint reachable?",
                    "Is the latest snapshot current?",
                    "Should a fresh governance report be requested?",
                ],
                recommended_next_actions=["Capture a fresh NEOS governance snapshot if the source has changed."],
            )
            priority = GovernancePrioritySummary(
                operational_priority="P4",
                deterministic_score=0,
                ranked_finding_ids=[],
                ranking_basis=["no_findings"],
            )
            work_package = None
        recommended_actions = list(dict.fromkeys(interpretation.recommended_next_actions))
        limitations = []
        if source_state.compatibility_state != "compatible":
            limitations.append(f"Source compatibility is {source_state.compatibility_state}.")
        if source_state.cache_state == "stale":
            limitations.append("Using last known governance snapshot.")
        if not source_state.available:
            limitations.append("Governance source unavailable.")
        if source_state.source_timestamp is None:
            limitations.append("Source timestamp unavailable.")
        if source_state.snapshot is not None and source_state.snapshot.readiness == "UNKNOWN":
            limitations.append("Readiness remains UNKNOWN in the source.")
        return interpretation, priority, work_package, recommended_actions, limitations

    def _programme_context(self, *, project_id: str | None, findings: list[GovernanceFindingContext]) -> dict[str, Any]:
        context: dict[str, Any] = {
            "downstream_only": True,
            "c1_project_contract": None,
            "c2_dependency_graph": None,
            "c3_change_impact": None,
            "c4_programme_roadmap": None,
            "c5_programme_packages": None,
        }
        if project_id is None:
            context["finding_count"] = len(findings)
            return context
        try:
            contract = self.project_service.current_project_contract(project_id)
            context["c1_project_contract"] = contract.model_dump(mode="json") if contract else None
        except Exception:
            context["c1_project_contract"] = None
        try:
            dependencies = self.project_service.project_dependency_graph(project_id, transitive=False)
            context["c2_dependency_graph"] = {
                "count": len(dependencies),
                "items": [item.model_dump(mode="json") for item in dependencies[:20]],
            }
        except Exception:
            context["c2_dependency_graph"] = None
        try:
            impact = self.project_service.change_impact({"project_id": project_id, "summary": "governance context"})
            context["c3_change_impact"] = impact.model_dump(mode="json")
        except Exception:
            context["c3_change_impact"] = None
        try:
            roadmap = self.project_service.programme_roadmap()
            context["c4_programme_roadmap"] = roadmap.model_dump(mode="json")
        except Exception:
            context["c4_programme_roadmap"] = None
        try:
            packages = self.project_service.programme_packages()
            context["c5_programme_packages"] = packages.model_dump(mode="json")
        except Exception:
            context["c5_programme_packages"] = None
        context["finding_count"] = len(findings)
        return context

    def _freshness(self, source_state: GovernanceSourceState) -> GovernanceFreshness:
        now = utc_now()
        if source_state.source_timestamp is None:
            return GovernanceFreshness(
                received_at=source_state.received_at,
                source_timestamp=None,
                age_seconds=None,
                state="unknown",
                notes=["Source timestamp unavailable."],
            )
        age = (now - source_state.source_timestamp).total_seconds()
        state: Literal["fresh", "stale", "unknown"] = "fresh" if age < 86_400 else "stale"
        notes = []
        if source_state.cache_state == "stale":
            notes.append("Cached data is stale.")
        if source_state.compatibility_state != "compatible":
            notes.append(f"Compatibility state is {source_state.compatibility_state}.")
        return GovernanceFreshness(
            received_at=source_state.received_at,
            source_timestamp=source_state.source_timestamp,
            age_seconds=age,
            state=state,
            notes=notes,
        )

    def _render_codex_prompt(
        self,
        finding: NeosGovernanceFinding,
        tier: PriorityTier,
        proposed_tasks: list[str],
        review_questions: list[str],
    ) -> str:
        tasks = "\n".join(f"- {task}" for task in proposed_tasks)
        questions = "\n".join(f"- {question}" for question in review_questions)
        return (
            "DRAFT - NOT EXECUTED\n\n"
            f"Source finding ID: {finding.finding_id}\n"
            f"Rule ID: {finding.rule_id}\n"
            f"Source severity: {finding.severity}\n"
            f"GAIA priority: {tier}\n"
            f"Canonical owner: {finding.canonical_owner or 'unknown'}\n"
            f"Recommended owner: {finding.recommended_owner or 'unknown'}\n"
            f"Snapshot ID: {finding.snapshot_id or 'unknown'}\n\n"
            "Source fact:\n"
            f"{json.dumps(finding.model_dump(mode='json'), indent=2, sort_keys=True)}\n\n"
            "Proposed tasks:\n"
            f"{tasks}\n\n"
            "Review questions:\n"
            f"{questions}\n\n"
            "Boundaries:\n"
            "- No NEOS mutation.\n"
            "- Human review required.\n"
            "- Draft only.\n"
        )

    def _brief_from_context(self, context: GovernanceContext) -> GovernanceBrief:
        snapshot_id = context.source.snapshot.snapshot_id if context.source.snapshot else None
        readiness = context.source.status.summary.get("readiness", context.source.status.status) if context.source.status else context.source.compatibility_state
        facts = [
            f"Estate readiness: {readiness}",
            f"Snapshot ID: {snapshot_id or 'none'}",
            f"Findings: {len(context.findings)}",
        ]
        if context.source.snapshot is not None:
            facts.append(f"NEOS version: {context.source.snapshot.neos_version or context.source.neos_version or 'unknown'}")
        unknowns = [
            item
            for item in [
                "Unknown readiness must remain unknown until NEOS says otherwise.",
                "Using cached context where the source is unavailable.",
                "Source timestamp missing." if context.source.source_timestamp is None else "",
            ]
            if item
        ]
        programme_impact = []
        if context.programme_context.get("c4_programme_roadmap"):
            programme_impact.append("Programme roadmap context available.")
        if context.programme_context.get("c5_programme_packages"):
            programme_impact.append("Programme package context available.")
        review_lines = [
            f"{item.source.rule_id}: {item.priority.operational_priority} - {item.interpretation.explanation}"
            for item in context.findings[:5]
        ] or ["No active governance findings."]
        markdown_lines = [
            "# Architecture Governance",
            "",
            f"Estate readiness: {readiness}",
            "",
            "Snapshot:",
            *[f"- {line}" for line in facts[1:]],
            "",
            "Top findings:",
            *[f"- {line}" for line in review_lines],
            "",
            "Unknowns:",
            *([f"- {line}" for line in unknowns] if unknowns else ["- None"]),
            "",
            "Programme impact:",
            *([f"- {line}" for line in programme_impact] if programme_impact else ["- Downstream-only context"]),
            "",
            "Recommended human reviews:",
            *([f"- {line}" for line in context.recommended_actions[:5]] if context.recommended_actions else ["- None"]),
        ]
        markdown = "\n".join(markdown_lines)
        return GovernanceBrief(
            estate_status=readiness,
            snapshot_id=snapshot_id,
            headline="Governance source unavailable." if not context.source.available else "Governance context ready.",
            facts=facts,
            unknowns=unknowns,
            programme_impact=programme_impact or ["Downstream-only context."],
            recommended_human_reviews=review_lines,
            markdown=markdown,
        )
