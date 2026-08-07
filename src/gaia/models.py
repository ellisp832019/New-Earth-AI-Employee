from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: str
    name: str
    root: Path
    access: Literal["read_only"] = "read_only"
    enabled: bool = True
    repository_type: str = "git"
    inspection_access: str = "read_only"
    output_access: str = "none"
    sensitivity: str = "internal"
    approved_extensions: set[str]
    excluded_directories: set[str] = Field(default_factory=set)
    excluded_filenames: set[str] = Field(default_factory=set)
    important_paths: list[str] = Field(default_factory=list)
    health_rules: dict[str, Any] = Field(default_factory=dict)
    release_rules: dict[str, Any] = Field(default_factory=dict)
    approval_requirements: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("root", mode="before")
    @classmethod
    def normalise_root(cls, value: Any) -> Path:
        return Path(value).expanduser().resolve(strict=False)

    @field_validator("approved_extensions")
    @classmethod
    def normalise_extensions(cls, values: set[str]) -> set[str]:
        return {value.lower() if value.startswith(".") else f".{value.lower()}" for value in values}

    def config_payload(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "root": str(self.root),
            "access": self.access,
            "enabled": self.enabled,
            "repository_type": self.repository_type,
            "inspection_access": self.inspection_access,
            "output_access": self.output_access,
            "sensitivity": self.sensitivity,
            "approved_extensions": sorted(self.approved_extensions),
            "excluded_directories": sorted(self.excluded_directories),
            "excluded_filenames": sorted(self.excluded_filenames),
            "important_paths": list(self.important_paths),
            "health_rules": self.health_rules,
            "release_rules": self.release_rules,
            "approval_requirements": self.approval_requirements,
            "metadata": self.metadata,
        }

    def public_payload(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "root": str(self.root),
            "access": self.access,
            "approved_extensions": sorted(self.approved_extensions),
            "excluded_directories": sorted(self.excluded_directories),
            "excluded_filenames": sorted(self.excluded_filenames),
            "important_paths": list(self.important_paths),
        }

    def config_fingerprint(self) -> str:
        import hashlib

        payload = json.dumps(self.config_payload(), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    category: str
    operation: str
    project_id: str | None = None
    outcome: Literal["allowed", "rejected", "success", "failure"]
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_classification: str | None = None


class DocumentRecord(BaseModel):
    project_id: str
    relative_path: str
    extension: str
    size_bytes: int
    modified_utc: datetime
    sha256: str
    tracked: bool | None = None
    indexing_status: Literal["indexed", "skipped", "failed"]
    warning: str | None = None
    scanned_at: datetime = Field(default_factory=utc_now)
    content: str | None = None


class GitCommandResult(BaseModel):
    operation: str
    args: list[str]
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    truncated: bool = False


class GitState(BaseModel):
    repository_root: str
    branch: str | None
    detached_head: bool = False
    commit_sha: str | None
    upstream_name: str | None = None
    is_clean: bool
    status_porcelain: list[str]
    recent_commits: list[str]
    branches: list[str]
    tags: list[str]
    remotes: list[str]
    ahead: int | None = None
    behind: int | None = None
    tracked_file_count: int
    tracked_modifications_count: int = 0
    untracked_item_count: int = 0
    untracked_files: list[str]
    changed_files: list[str]
    warnings: list[str] = Field(default_factory=list)


class RepositorySnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    project_name: str
    project_root: str
    created_at: datetime = Field(default_factory=utc_now)
    git: GitState
    document_count: int
    indexed_count: int
    skipped_count: int
    failed_count: int
    counts_by_extension: dict[str, int]
    scan_warnings: list[str]
    important_paths: dict[str, bool]


class SearchResult(BaseModel):
    relative_path: str
    extension: str
    snippet: str
    score: float | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    database_path: str
    fts5_available: bool


class CapabilityDescriptor(BaseModel):
    capability_id: str
    version: str
    state: Literal["enabled", "degraded", "disabled"]
    summary: str
    gated_by: list[str] = Field(default_factory=list)
    requires_signing: bool = False
    enabled: bool = True


class SigningKeySummary(BaseModel):
    key_id: str
    key_name: str
    public_key: str
    status: Literal["active", "rotated", "revoked"]
    created_at: datetime = Field(default_factory=utc_now)
    revoked_at: datetime | None = None
    rotated_from_key_id: str | None = None
    last_used_at: datetime | None = None
    signing_enabled: bool = False


class ProvenanceManifestRecord(BaseModel):
    manifest_id: str
    manifest_version: int
    subject_kind: str
    subject_id: str
    subject_version: int
    content_hash: str
    canonical_json: str
    created_at: datetime = Field(default_factory=utc_now)
    signing_key_id: str | None = None
    signature: str | None = None
    signature_status: Literal[
        "unsigned",
        "hash_verified",
        "hash_chained",
        "cryptographically_signed",
        "signature_invalid",
        "signing_key_revoked",
    ] = "unsigned"
    key_status: Literal["active", "revoked", "rotated", "unknown"] = "unknown"
    chain_id: str | None = None
    chain_sequence: int | None = None
    package_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrustAlertRecord(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    alert_type: str
    severity: Literal["info", "warning", "critical"]
    status: Literal["open", "acknowledged", "resolved"] = "open"
    title: str
    message: str
    source_kind: str
    source_id: str
    created_at: datetime = Field(default_factory=utc_now)
    acknowledged_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


ProjectHealthStatus = Literal["healthy", "attention", "blocked", "unknown"]


class ProjectHealthEvidenceReference(BaseModel):
    evidence_kind: str
    evidence_id: str | None = None
    description: str
    freshness: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProjectHealthSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: int = 1
    project_id: str
    project_name: str
    project_root: str
    project_configuration_fingerprint: str
    capture_timestamp: datetime = Field(default_factory=utc_now)
    normalized_status: ProjectHealthStatus = "unknown"
    reason_codes: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    blocking_conditions: list[str] = Field(default_factory=list)
    attention_conditions: list[str] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)
    evidence_references: list[ProjectHealthEvidenceReference] = Field(default_factory=list)
    normalized_payload: dict[str, Any] = Field(default_factory=dict)
    provenance_reference: str | None = None
    audit_event_id: str | None = None
    content_fingerprint: str = ""


class ProjectHealthPortfolioEntry(BaseModel):
    project_id: str
    project_name: str
    project_root: str
    enabled: bool
    repository_type: str
    latest_snapshot_id: str | None = None
    latest_capture_timestamp: datetime | None = None
    normalized_status: ProjectHealthStatus = "unknown"
    snapshot_count: int = 0
    evidence_freshness: str = "unknown"
    reason_codes: list[str] = Field(default_factory=list)
    latest_snapshot: ProjectHealthSnapshot | None = None


class ProjectHealthPortfolio(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    enabled_project_count: int = 0
    projects: list[ProjectHealthPortfolioEntry] = Field(default_factory=list)
    projects_without_snapshots: list[str] = Field(default_factory=list)
    counts_by_status: dict[str, int] = Field(default_factory=dict)
    latest_snapshot_ids: dict[str, str] = Field(default_factory=dict)


ChangeClass = Literal[
    "snapshot_delta",
    "health_transition",
    "branch_change",
    "head_change",
    "working_tree_change",
    "upstream_divergence",
    "important_path_change",
    "evidence_freshness_change",
    "configuration_change",
    "release_drift",
    "contract_drift",
    "documentation_drift",
    "dependency_drift",
    "test_regression",
    "untracked_work",
    "not_evaluated",
]

ChangeDirection = Literal["improved", "degraded", "changed", "unchanged", "unknown"]
ChangeSeverity = Literal["info", "low", "medium", "high", "critical", "not_evaluated"]
ChangeConfidence = Literal["high", "medium", "low", "unknown"]
ChangeFindingStatus = Literal["active", "suppressed", "not_evaluated"]
ChangeComparisonStatus = Literal["compared", "no_meaningful_change", "insufficient_evidence", "not_evaluated"]


class ProjectChangeComparison(BaseModel):
    comparison_id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: int = 1
    detector_version: str
    project_id: str
    comparison_kind: str = "explicit"
    previous_snapshot_id: str
    current_snapshot_id: str
    previous_snapshot_fingerprint: str
    current_snapshot_fingerprint: str
    capture_timestamp: datetime = Field(default_factory=utc_now)
    comparison_status: ChangeComparisonStatus = "compared"
    meaningful_change_detected: bool = False
    finding_count: int = 0
    finding_ids: list[str] = Field(default_factory=list)
    detector_outcomes: list[dict[str, Any]] = Field(default_factory=list)
    normalized_payload: dict[str, Any] = Field(default_factory=dict)
    provenance_reference: str | None = None
    audit_event_id: str | None = None
    content_fingerprint: str = ""


class ProjectChangeFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: int = 1
    comparison_id: str
    project_id: str
    finding_type: ChangeClass
    change_class: ChangeClass
    severity: ChangeSeverity = "info"
    direction: ChangeDirection = "unknown"
    confidence: ChangeConfidence = "unknown"
    status: ChangeFindingStatus = "active"
    capture_timestamp: datetime = Field(default_factory=utc_now)
    previous_snapshot_id: str
    current_snapshot_id: str
    previous_snapshot_fingerprint: str
    current_snapshot_fingerprint: str
    reason_codes: list[str] = Field(default_factory=list)
    explanation: str = ""
    evidence_references: list[ProjectHealthEvidenceReference] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    normalized_payload: dict[str, Any] = Field(default_factory=dict)
    detector_version: str = ""
    provenance_reference: str | None = None
    audit_event_id: str | None = None
    content_fingerprint: str = ""


class ProjectChangePortfolioEntry(BaseModel):
    project_id: str
    project_name: str
    latest_health_status: ProjectHealthStatus = "unknown"
    latest_meaningful_change_timestamp: datetime | None = None
    latest_comparison_id: str | None = None
    latest_comparison_freshness: str = "unknown"
    stale_evidence: bool = False
    counts_by_severity: dict[str, int] = Field(default_factory=dict)
    latest_findings: list[ProjectChangeFinding] = Field(default_factory=list)


class ProjectChangePortfolio(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    projects: list[ProjectChangePortfolioEntry] = Field(default_factory=list)
    counts_by_severity: dict[str, int] = Field(default_factory=dict)
    counts_by_change_class: dict[str, int] = Field(default_factory=dict)
