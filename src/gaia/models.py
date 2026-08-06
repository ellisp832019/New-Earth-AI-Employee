from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProjectConfig(BaseModel):
    project_id: str
    name: str
    root: Path
    access: Literal["read_only"] = "read_only"
    approved_extensions: set[str]
    excluded_directories: set[str] = Field(default_factory=set)
    excluded_filenames: set[str] = Field(default_factory=set)
    important_paths: list[str] = Field(default_factory=list)

    @field_validator("approved_extensions")
    @classmethod
    def normalise_extensions(cls, values: set[str]) -> set[str]:
        return {value.lower() if value.startswith(".") else f".{value.lower()}" for value in values}


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
    commit_sha: str | None
    is_clean: bool
    status_porcelain: list[str]
    recent_commits: list[str]
    branches: list[str]
    tags: list[str]
    remotes: list[str]
    ahead: int | None = None
    behind: int | None = None
    tracked_file_count: int
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
