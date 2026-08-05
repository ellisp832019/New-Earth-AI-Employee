from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from gaia.audit import AuditRecorder
from gaia.config import Settings
from gaia.db import Database
from gaia.models import utc_now
from gaia.service import ProjectService
from gaia.workflows import ApprovalRecord, TaskWorkflowService

ManifestActionType = Literal[
    "create_output_file",
    "update_output_file",
    "export_draft",
    "export_report",
    "export_daily_brief",
    "create_generated_document",
    "rollback_output_file",
]
ManifestRisk = Literal["low", "medium", "high", "prohibited"]
ActionStatus = Literal[
    "proposed",
    "awaiting_approval",
    "approved",
    "executing",
    "completed",
    "failed",
    "invalidated",
    "rolled_back",
    "cancelled",
]
ApprovalStatus = Literal["pending", "approved_for_manual_use", "rejected", "expired", "cancelled", "invalidated"]
OVERWRITE_POLICIES = {"deny", "backup_then_replace", "allow"}
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *{f"com{i}" for i in range(1, 10)},
    *{f"lpt{i}" for i in range(1, 10)},
}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def _json_loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    text = str(value).strip()
    if not text:
        return default
    return json.loads(text)


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return utc_now().isoformat()


class PermissionManifest(BaseModel):
    manifest_id: str = Field(default_factory=lambda: str(uuid4()))
    manifest_version: int = 1
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    allowed_action_types: list[ManifestActionType] = Field(default_factory=list)
    allowed_target_roots: list[str] = Field(default_factory=list)
    allowed_file_extensions: list[str] = Field(default_factory=list)
    denied_path_patterns: list[str] = Field(default_factory=list)
    maximum_file_size: int = 0
    overwrite_policy: Literal["deny", "backup_then_replace", "allow"] = "deny"
    backup_requirement: bool = True
    rollback_requirement: bool = True
    approval_requirement: bool = True
    risk_ceiling: ManifestRisk = "low"
    expiry_timestamp: datetime | None = None
    creation_source: str = "manual"
    created_at: datetime = Field(default_factory=utc_now)
    enabled: bool = False
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None

    @field_validator("description", "creation_source", "reviewed_by", "review_notes")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class PermissionManifestCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    allowed_action_types: list[ManifestActionType] = Field(default_factory=list)
    allowed_target_roots: list[str] = Field(default_factory=list)
    allowed_file_extensions: list[str] = Field(default_factory=list)
    denied_path_patterns: list[str] = Field(default_factory=list)
    maximum_file_size: int = 0
    overwrite_policy: Literal["deny", "backup_then_replace", "allow"] = "deny"
    backup_requirement: bool = True
    rollback_requirement: bool = True
    approval_requirement: bool = True
    risk_ceiling: ManifestRisk = "low"
    expiry_timestamp: datetime | None = None
    creation_source: str = "manual"
    enabled: bool = False


class PermissionManifestDecisionRequest(BaseModel):
    version: int
    reviewer: str = "manual"
    review_notes: str = ""
    enabled: bool = True


class OutputAction(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: ManifestActionType
    title: str = Field(min_length=1, max_length=200)
    project_id: str
    source_task_id: str | None = None
    source_draft_id: str | None = None
    source_draft_revision: int | None = None
    source_approval_id: str | None = None
    manifest_id: str
    manifest_version: int
    canonical_target: str
    proposed_content: str = ""
    previous_content_hash: str | None = None
    proposed_content_hash: str
    preview: str = ""
    diff: str = ""
    risk: ManifestRisk = "low"
    status: ActionStatus = "proposed"
    created_at: datetime = Field(default_factory=utc_now)
    expiry_timestamp: datetime | None = None
    execution_time: datetime | None = None
    execution_receipt_id: str | None = None
    approval_id: str | None = None
    approval_binding_hash: str | None = None
    approval_status: ApprovalStatus | None = None
    approval_decision_timestamp: datetime | None = None
    approval_reviewer: str | None = None
    approval_reason: str | None = None
    denial_reason: str | None = None
    backup_path: str | None = None
    rollback_available: bool = False
    operator: str | None = None
    warnings: list[str] = Field(default_factory=list)
    result: str | None = None


class OutputActionCreateRequest(BaseModel):
    action_type: ManifestActionType
    title: str = Field(min_length=1, max_length=200)
    project_id: str
    source_task_id: str | None = None
    source_draft_id: str | None = None
    source_draft_revision: int | None = None
    source_approval_id: str | None = None
    manifest_id: str
    target_path: str
    content: str | None = None
    content_source: Literal["manual", "draft", "report", "brief"] = "manual"
    report_project_id: str | None = None
    brief_project_id: str | None = None
    risk: ManifestRisk = "low"
    expiry_timestamp: datetime | None = None


class OutputActionPreviewRecord(BaseModel):
    preview_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    created_at: datetime = Field(default_factory=utc_now)
    preview: str = ""
    diff: str = ""
    previous_content_hash: str | None = None
    proposed_content_hash: str = ""
    target_path: str


class ExecutionReceiptRecord(BaseModel):
    receipt_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    approval_id: str | None = None
    manifest_id: str
    manifest_version: int
    source_draft_id: str | None = None
    source_draft_revision: int | None = None
    target_path: str
    previous_hash: str | None = None
    resulting_hash: str
    backup_path: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    operator: str = "manual"
    result: str = "completed"
    warnings: list[str] = Field(default_factory=list)
    rollback_available: bool = False


class BackupRecord(BaseModel):
    backup_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    target_path: str
    backup_path: str
    content_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    verified: bool = False


class RollbackRecord(BaseModel):
    rollback_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    receipt_id: str | None = None
    target_path: str
    backup_path: str
    previous_hash: str | None = None
    resulting_hash: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    executed_at: datetime | None = None
    status: Literal["proposed", "executed", "failed", "cancelled"] = "proposed"
    reason: str | None = None


class OutputWorkspaceError(Exception):
    pass


class PermissionDeniedError(OutputWorkspaceError):
    pass


class PathSafetyError(PermissionError):
    pass


def _contains_hidden_git_path(parts: tuple[str, ...]) -> bool:
    return any(part.lower() == ".git" for part in parts)


def _is_reserved_windows_name(name: str) -> bool:
    stem = name.split(".")[0].lower()
    return stem in WINDOWS_RESERVED_NAMES


def _is_device_or_unc_path(text: str) -> bool:
    normalised = text.replace("/", "\\")
    return normalised.startswith("\\\\?\\") or normalised.startswith("\\\\.\\") or normalised.startswith("\\\\")


def _has_ads(text: str) -> bool:
    if len(text) >= 2 and text[1] == ":" and re.match(r"^[A-Za-z]:", text):
        return text.count(":") > 1
    return ":" in text


def _path_contains_traversal(text: str) -> bool:
    parts = re.split(r"[\\/]+", text)
    return any(part == ".." for part in parts)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


class OutputWorkspaceService:
    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.audit = AuditRecorder(self.database)
        self.project_service = ProjectService(settings, self.database)
        self.workflow_service = TaskWorkflowService(settings, self.database)
        self.repo_root = Path.cwd().resolve()
        self.workspace_root = self.repo_root / "workspace"
        self.allowed_runtime_roots = [
            self.workspace_root / "approved_outputs",
            self.workspace_root / "exports",
            self.workspace_root / "backups",
            self.workspace_root / "receipts",
            self.workspace_root / "rollback",
        ]
        for root in self.allowed_runtime_roots:
            root.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # Permission manifests
    # ---------------------------------------------------------------------
    def _manifest_row(self, manifest_id: str) -> Any:
        row = self.database.connection.execute(
            "SELECT * FROM permission_manifests WHERE manifest_id = ?",
            (manifest_id,),
        ).fetchone()
        if not row:
            raise OutputWorkspaceError(f"Permission manifest not found: {manifest_id}")
        return row

    def _manifest_from_row(self, row: Any) -> PermissionManifest:
        data = dict(row)
        data["allowed_action_types"] = _json_loads(data.pop("allowed_action_types_json"), [])
        data["allowed_target_roots"] = _json_loads(data.pop("allowed_target_roots_json"), [])
        data["allowed_file_extensions"] = _json_loads(data.pop("allowed_file_extensions_json"), [])
        data["denied_path_patterns"] = _json_loads(data.pop("denied_path_patterns_json"), [])
        data["expiry_timestamp"] = (
            datetime.fromisoformat(str(data["expiry_timestamp"])) if data.get("expiry_timestamp") else None
        )
        data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
        data["reviewed_at"] = (
            datetime.fromisoformat(str(data["reviewed_at"])) if data.get("reviewed_at") else None
        )
        return PermissionManifest.model_validate(data)

    def _write_manifest(self, manifest: PermissionManifest) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO permission_manifests(
                    manifest_id, manifest_version, name, description, allowed_action_types_json,
                    allowed_target_roots_json, allowed_file_extensions_json, denied_path_patterns_json,
                    maximum_file_size, overwrite_policy, backup_requirement, rollback_requirement,
                    approval_requirement, risk_ceiling, expiry_timestamp, creation_source, created_at,
                    enabled, reviewed_by, reviewed_at, review_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest.manifest_id,
                    manifest.manifest_version,
                    manifest.name,
                    manifest.description,
                    _json_dumps(manifest.allowed_action_types),
                    _json_dumps(manifest.allowed_target_roots),
                    _json_dumps(manifest.allowed_file_extensions),
                    _json_dumps(manifest.denied_path_patterns),
                    manifest.maximum_file_size,
                    manifest.overwrite_policy,
                    int(manifest.backup_requirement),
                    int(manifest.rollback_requirement),
                    int(manifest.approval_requirement),
                    manifest.risk_ceiling,
                    manifest.expiry_timestamp.isoformat() if manifest.expiry_timestamp else None,
                    manifest.creation_source,
                    manifest.created_at.isoformat(),
                    int(manifest.enabled),
                    manifest.reviewed_by,
                    manifest.reviewed_at.isoformat() if manifest.reviewed_at else None,
                    manifest.review_notes,
                ),
            )

    def list_permission_manifests(self) -> list[PermissionManifest]:
        rows = self.database.connection.execute(
            "SELECT * FROM permission_manifests ORDER BY created_at DESC",
        ).fetchall()
        return [self._manifest_from_row(row) for row in rows]

    def get_permission_manifest(self, manifest_id: str) -> PermissionManifest:
        return self._manifest_from_row(self._manifest_row(manifest_id))

    def create_permission_manifest(self, request: PermissionManifestCreateRequest) -> PermissionManifest:
        manifest = PermissionManifest(
            name=request.name,
            description=request.description,
            allowed_action_types=request.allowed_action_types,
            allowed_target_roots=request.allowed_target_roots,
            allowed_file_extensions=request.allowed_file_extensions,
            denied_path_patterns=request.denied_path_patterns,
            maximum_file_size=request.maximum_file_size,
            overwrite_policy=request.overwrite_policy,
            backup_requirement=request.backup_requirement,
            rollback_requirement=request.rollback_requirement,
            approval_requirement=request.approval_requirement,
            risk_ceiling=request.risk_ceiling,
            expiry_timestamp=request.expiry_timestamp,
            creation_source=request.creation_source,
            enabled=request.enabled,
        )
        self._write_manifest(manifest)
        self.audit.record(
            category="permissions",
            operation="create_manifest",
            project_id=None,
            outcome="success",
            metadata={"manifest_id": manifest.manifest_id, "enabled": manifest.enabled},
        )
        return manifest

    def update_permission_manifest(self, manifest_id: str, request: PermissionManifestDecisionRequest) -> PermissionManifest:
        manifest = self.get_permission_manifest(manifest_id)
        if manifest.manifest_version != request.version:
            raise OutputWorkspaceError("Permission manifest version mismatch.")
        manifest.manifest_version += 1
        manifest.reviewed_by = request.reviewer
        manifest.reviewed_at = utc_now()
        manifest.review_notes = request.review_notes
        manifest.enabled = request.enabled
        self._write_manifest(manifest)
        self.audit.record(
            category="permissions",
            operation="update_manifest",
            outcome="success",
            metadata={"manifest_id": manifest.manifest_id, "enabled": manifest.enabled},
        )
        return manifest

    def validate_permission_manifest(self, manifest_id: str) -> dict[str, Any]:
        manifest = self.get_permission_manifest(manifest_id)
        problems: list[str] = []
        if not manifest.allowed_action_types:
            problems.append("No allowed action types configured.")
        if not manifest.allowed_target_roots:
            problems.append("No allowed target roots configured.")
        if manifest.overwrite_policy not in OVERWRITE_POLICIES:
            problems.append("Invalid overwrite policy.")
        if manifest.maximum_file_size < 0:
            problems.append("Maximum file size must be non-negative.")
        for root in manifest.allowed_target_roots:
            candidate = self._resolve_workspace_root(root)
            if not candidate.exists():
                problems.append(f"Allowed root does not exist: {root}")
        return {
            "manifest_id": manifest.manifest_id,
            "manifest_version": manifest.manifest_version,
            "enabled": manifest.enabled,
            "problems": problems,
            "valid": not problems and manifest.enabled,
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _action_row(self, action_id: str) -> Any:
        row = self.database.connection.execute(
            "SELECT * FROM output_actions WHERE action_id = ?",
            (action_id,),
        ).fetchone()
        if not row:
            raise OutputWorkspaceError(f"Action not found: {action_id}")
        return row

    def _action_from_row(self, row: Any) -> OutputAction:
        data = dict(row)
        data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
        data["expiry_timestamp"] = (
            datetime.fromisoformat(str(data["expiry_timestamp"])) if data.get("expiry_timestamp") else None
        )
        data["execution_time"] = (
            datetime.fromisoformat(str(data["execution_time"])) if data.get("execution_time") else None
        )
        data["approval_decision_timestamp"] = (
            datetime.fromisoformat(str(data["approval_decision_timestamp"]))
            if data.get("approval_decision_timestamp")
            else None
        )
        data["warnings"] = _json_loads(data.pop("warnings_json"), [])
        return OutputAction.model_validate(data)

    def _write_action(self, action: OutputAction) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO output_actions(
                    action_id, action_type, title, project_id, source_task_id, source_draft_id,
                    source_draft_revision, source_approval_id, manifest_id, manifest_version,
                    canonical_target, proposed_content, previous_content_hash, proposed_content_hash,
                    preview, diff, risk, status, created_at, expiry_timestamp, execution_time,
                    execution_receipt_id, approval_id, approval_binding_hash, approval_status,
                    approval_decision_timestamp, approval_reviewer, approval_reason, denial_reason,
                    backup_path, rollback_available, operator, warnings_json, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.action_id,
                    action.action_type,
                    action.title,
                    action.project_id,
                    action.source_task_id,
                    action.source_draft_id,
                    action.source_draft_revision,
                    action.source_approval_id,
                    action.manifest_id,
                    action.manifest_version,
                    action.canonical_target,
                    action.proposed_content,
                    action.previous_content_hash,
                    action.proposed_content_hash,
                    action.preview,
                    action.diff,
                    action.risk,
                    action.status,
                    action.created_at.isoformat(),
                    action.expiry_timestamp.isoformat() if action.expiry_timestamp else None,
                    action.execution_time.isoformat() if action.execution_time else None,
                    action.execution_receipt_id,
                    action.approval_id,
                    action.approval_binding_hash,
                    action.approval_status,
                    action.approval_decision_timestamp.isoformat() if action.approval_decision_timestamp else None,
                    action.approval_reviewer,
                    action.approval_reason,
                    action.denial_reason,
                    action.backup_path,
                    int(action.rollback_available),
                    action.operator,
                    _json_dumps(action.warnings),
                    action.result,
                ),
            )

    def list_actions(self, *, project_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0) -> list[OutputAction]:
        clauses = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.connection.execute(
            f"SELECT * FROM output_actions {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, max(1, min(limit, 500)), max(0, offset)),
        ).fetchall()
        return [self._action_from_row(row) for row in rows]

    def get_action(self, action_id: str) -> OutputAction:
        return self._action_from_row(self._action_row(action_id))

    def _resolve_workspace_root(self, root: str) -> Path:
        candidate = (self.repo_root / root).resolve()
        if self.repo_root not in candidate.parents and candidate != self.repo_root:
            raise PathSafetyError("Manifest target root escapes the GAIA repository.")
        return candidate

    def _canonical_target(self, manifest: PermissionManifest, requested_target: str) -> Path:
        text = requested_target.strip()
        if not text:
            raise PathSafetyError("Target path is empty.")
        if _is_device_or_unc_path(text):
            raise PathSafetyError("UNC and device paths are not allowed.")
        if _has_ads(text):
            raise PathSafetyError("Alternate data streams are not allowed.")
        if _path_contains_traversal(text):
            raise PathSafetyError("Path traversal is not allowed.")
        if Path(text).is_absolute():
            raise PathSafetyError("Absolute targets are not allowed.")
        relative = Path(text.replace("\\", "/"))
        if _contains_hidden_git_path(relative.parts):
            raise PathSafetyError("Hidden Git paths are not allowed.")
        for part in relative.parts:
            if _is_reserved_windows_name(part):
                raise PathSafetyError(f"Reserved Windows filename is not allowed: {part}")
        resolved_target = (self.repo_root / relative).resolve(strict=False)
        allowed_roots = [self._resolve_workspace_root(root).resolve(strict=False) for root in manifest.allowed_target_roots]
        if not any(
            resolved_target == root or root in resolved_target.parents
            for root in allowed_roots
        ):
            raise PermissionDeniedError("Requested target is outside the manifest allowed roots.")
        return resolved_target

    def _resolve_action_content(self, request: OutputActionCreateRequest, manifest: PermissionManifest) -> tuple[str, list[str]]:
        warnings: list[str] = []
        if request.action_type not in manifest.allowed_action_types:
            raise PermissionDeniedError("Manifest does not allow this action type.")
        if request.risk > manifest.risk_ceiling:
            raise PermissionDeniedError("Requested action risk exceeds the manifest ceiling.")
        if request.content_source == "manual":
            content = request.content or ""
        elif request.content_source == "draft":
            if not request.source_draft_id:
                raise OutputWorkspaceError("Draft source requires a source draft ID.")
            draft = self.workflow_service.get_draft(request.source_draft_id)
            revisions = self.workflow_service.draft_revisions(draft.draft_id)
            if not revisions:
                raise OutputWorkspaceError("Draft has no revisions.")
            if request.source_draft_revision is not None and request.source_draft_revision != draft.current_revision:
                raise OutputWorkspaceError("Requested draft revision does not match the current draft.")
            content = revisions[-1].content
        elif request.content_source == "report":
            project_id = request.report_project_id or request.project_id
            content = self.project_service.foundation_report(project_id, "markdown")
        elif request.content_source == "brief":
            project_id = request.brief_project_id or request.project_id
            brief = self.workflow_service.briefs_latest(project_id) or self.workflow_service.daily_brief(project_id)
            content = brief.markdown
        else:
            raise OutputWorkspaceError("Unsupported content source.")
        if len(content.encode("utf-8")) > manifest.maximum_file_size > 0:
            raise PermissionDeniedError("Proposed content exceeds the manifest size limit.")
        return content, warnings

    def _load_existing_target(self, target: Path) -> tuple[str | None, str | None]:
        if not target.exists():
            return None, None
        if target.is_dir():
            raise PathSafetyError("Target path points to a directory.")
        return target.read_text(encoding="utf-8"), _hash_file(target)

    def _preview(self, previous_content: str | None, proposed_content: str, target: str) -> tuple[str, str]:
        preview = proposed_content if len(proposed_content) <= 5000 else proposed_content[:5000] + "\n...[truncated]..."
        before_lines = [] if previous_content is None else previous_content.splitlines(keepends=True)
        after_lines = proposed_content.splitlines(keepends=True)
        diff = "".join(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"a/{target}",
                tofile=f"b/{target}",
                lineterm="",
            )
        )
        return preview, diff

    def create_action(self, request: OutputActionCreateRequest) -> OutputAction:
        manifest = self.get_permission_manifest(request.manifest_id)
        if not manifest.enabled:
            raise PermissionDeniedError("Permission manifest is disabled.")
        if manifest.expiry_timestamp and manifest.expiry_timestamp < utc_now():
            raise PermissionDeniedError("Permission manifest has expired.")
        target = self._canonical_target(manifest, request.target_path)
        proposed_content, warnings = self._resolve_action_content(request, manifest)
        previous_content, previous_hash = self._load_existing_target(target)
        preview, diff = self._preview(previous_content, proposed_content, _relative_display(target, self.repo_root))
        action = OutputAction(
            action_type=request.action_type,
            title=request.title,
            project_id=request.project_id,
            source_task_id=request.source_task_id,
            source_draft_id=request.source_draft_id,
            source_draft_revision=request.source_draft_revision,
            source_approval_id=request.source_approval_id,
            manifest_id=manifest.manifest_id,
            manifest_version=manifest.manifest_version,
            canonical_target=_relative_display(target, self.repo_root),
            proposed_content=proposed_content,
            previous_content_hash=previous_hash,
            proposed_content_hash=_hash_content(proposed_content),
            preview=preview,
            diff=diff,
            risk=request.risk,
            expiry_timestamp=request.expiry_timestamp,
            warnings=warnings,
        )
        self._write_action(action)
        self.audit.record(
            category="actions",
            operation="create",
            project_id=request.project_id,
            outcome="success",
            metadata={"action_id": action.action_id, "manifest_id": manifest.manifest_id},
        )
        self._write_preview(
            OutputActionPreviewRecord(
                action_id=action.action_id,
                preview=preview,
                diff=diff,
                previous_content_hash=previous_hash,
                proposed_content_hash=action.proposed_content_hash,
                target_path=action.canonical_target,
            )
        )
        return action

    def _write_preview(self, preview: OutputActionPreviewRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT INTO action_previews(
                    preview_id, action_id, created_at, preview, diff,
                    previous_content_hash, proposed_content_hash, target_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preview.preview_id,
                    preview.action_id,
                    preview.created_at.isoformat(),
                    preview.preview,
                    preview.diff,
                    preview.previous_content_hash,
                    preview.proposed_content_hash,
                    preview.target_path,
                ),
            )

    def action_previews(self, action_id: str) -> list[OutputActionPreviewRecord]:
        rows = self.database.connection.execute(
            "SELECT * FROM action_previews WHERE action_id = ? ORDER BY created_at ASC",
            (action_id,),
        ).fetchall()
        previews: list[OutputActionPreviewRecord] = []
        for row in rows:
            data = dict(row)
            data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
            previews.append(OutputActionPreviewRecord.model_validate(data))
        return previews

    def request_approval(self, action_id: str, reviewer: str = "manual", decision_reason: str = "") -> ApprovalRecord:
        action = self.get_action(action_id)
        if action.status not in {"proposed", "awaiting_approval"}:
            raise PermissionDeniedError("Action is not awaiting approval.")
        manifest = self.get_permission_manifest(action.manifest_id)
        binding = _hash_content(
            _json_dumps(
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type,
                    "canonical_target": action.canonical_target,
                    "manifest_id": action.manifest_id,
                    "manifest_version": action.manifest_version,
                    "proposed_content_hash": action.proposed_content_hash,
                    "source_draft_revision": action.source_draft_revision,
                    "risk": action.risk,
                }
            )
        )
        approval = ApprovalRecord(
            request_type="action_execution",
            title=action.title,
            description=f"Approval for action {action.action_id}",
            project_id=action.project_id,
            source_task_id=action.source_task_id,
            source_draft_id=action.source_draft_id,
            requesting_source="manual",
            proposed_action=action.action_type,
            exact_target_description=action.canonical_target,
            write_boundary="gaia-owned-output-workspace",
            risk_level=action.risk,
            preview_summary=action.preview,
            approved_content_hash=action.proposed_content_hash,
            audit_references=[action.action_id],
            action_id=action.action_id,
            action_type=action.action_type,
            manifest_id=action.manifest_id,
            manifest_version=action.manifest_version,
            canonical_target=action.canonical_target,
            previous_content_hash=action.previous_content_hash,
            proposed_content_hash=action.proposed_content_hash,
            approval_binding_hash=binding,
            approval_scope="action_execution",
            expiry_timestamp=action.expiry_timestamp,
        )
        approval.reviewer = reviewer
        approval.decision_reason = decision_reason or "Requested for manual review"
        approval.status = "pending"
        approval.version = 1
        # Persist the approval with the extra action-binding columns.
        self._write_action_approval(approval, action, manifest.manifest_version, binding)
        action.approval_id = approval.approval_id
        action.approval_binding_hash = binding
        action.approval_status = "pending"
        action.status = "awaiting_approval"
        self._write_action(action)
        self.audit.record(
            category="actions",
            operation="request_approval",
            project_id=action.project_id,
            outcome="success",
            metadata={"action_id": action.action_id, "approval_id": approval.approval_id},
        )
        return approval

    def _write_action_approval(self, approval: ApprovalRecord, action: OutputAction, manifest_version: int, binding: str) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO approvals(
                    approval_id, request_type, title, description, project_id, source_task_id,
                    source_draft_id, requesting_source, proposed_action, exact_target_description,
                    write_boundary, risk_level, preview_summary, approved_content_hash, created_at,
                    expiry_timestamp, status, reviewer, decision_timestamp, decision_reason,
                    audit_references_json, invalidation_reason, version, action_id, action_type,
                    manifest_id, manifest_version, canonical_target, previous_content_hash,
                    proposed_content_hash, approval_binding_hash, approval_scope
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.approval_id,
                    approval.request_type,
                    approval.title,
                    approval.description,
                    approval.project_id,
                    approval.source_task_id,
                    approval.source_draft_id,
                    approval.requesting_source,
                    approval.proposed_action,
                    approval.exact_target_description,
                    approval.write_boundary,
                    approval.risk_level,
                    approval.preview_summary,
                    approval.approved_content_hash,
                    approval.created_at.isoformat(),
                    approval.expiry_timestamp.isoformat() if approval.expiry_timestamp else None,
                    approval.status,
                    approval.reviewer,
                    approval.decision_timestamp.isoformat() if approval.decision_timestamp else None,
                    approval.decision_reason,
                    _json_dumps(approval.audit_references),
                    approval.invalidation_reason,
                    approval.version,
                    action.action_id,
                    action.action_type,
                    action.manifest_id,
                    manifest_version,
                    action.canonical_target,
                    action.previous_content_hash,
                    action.proposed_content_hash,
                    binding,
                    "action_execution",
                ),
            )

    def _approval_from_row(self, row: Any) -> ApprovalRecord:
        data = dict(row)
        data["expiry_timestamp"] = (
            datetime.fromisoformat(str(data["expiry_timestamp"])) if data.get("expiry_timestamp") else None
        )
        data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
        data["decision_timestamp"] = (
            datetime.fromisoformat(str(data["decision_timestamp"])) if data.get("decision_timestamp") else None
        )
        data["audit_references"] = _json_loads(data.pop("audit_references_json"), [])
        return ApprovalRecord.model_validate(data)

    def _update_action_from_approval(self, approval: ApprovalRecord) -> None:
        row = self.database.connection.execute(
            "SELECT * FROM output_actions WHERE approval_id = ?",
            (approval.approval_id,),
        ).fetchone()
        if not row:
            return
        action = self._action_from_row(row)
        action.approval_status = approval.status
        action.approval_decision_timestamp = approval.decision_timestamp
        action.approval_reviewer = approval.reviewer
        action.approval_reason = approval.decision_reason
        if approval.status == "approved_for_manual_use":
            action.status = "approved"
        elif approval.status in {"rejected", "cancelled", "expired", "invalidated"}:
            action.status = "invalidated"
            action.denial_reason = approval.invalidation_reason or approval.decision_reason or approval.status
        self._write_action(action)

    def approval_for_action(self, action_id: str) -> ApprovalRecord | None:
        action = self.get_action(action_id)
        if not action.approval_id:
            return None
        row = self.database.connection.execute(
            "SELECT * FROM approvals WHERE approval_id = ?",
            (action.approval_id,),
        ).fetchone()
        return self._approval_from_row(row) if row else None

    def list_approvals(self, *, project_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0) -> list[ApprovalRecord]:
        clauses = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.connection.execute(
            f"SELECT * FROM approvals {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, max(1, min(limit, 500)), max(0, offset)),
        ).fetchall()
        return [self._approval_from_row(row) for row in rows]

    def approve_action(self, action_id: str, reviewer: str = "manual", decision_reason: str = "") -> ApprovalRecord:
        action = self.get_action(action_id)
        approval = self.approval_for_action(action_id)
        if approval is None:
            raise OutputWorkspaceError("No approval has been requested for this action.")
        if approval.status != "pending":
            raise PermissionDeniedError("Approval is not pending.")
        if approval.expiry_timestamp and approval.expiry_timestamp < utc_now():
            raise PermissionDeniedError("Approval has expired.")
        approval.status = "approved_for_manual_use"
        approval.reviewer = reviewer
        approval.decision_timestamp = utc_now()
        approval.decision_reason = decision_reason or "Approved for manual use"
        approval.version += 1
        with self.database.connection:
            self.database.connection.execute(
                """
                UPDATE approvals
                SET status = ?, reviewer = ?, decision_timestamp = ?, decision_reason = ?, version = ?
                WHERE approval_id = ?
                """,
                (
                    approval.status,
                    approval.reviewer,
                    approval.decision_timestamp.isoformat(),
                    approval.decision_reason,
                    approval.version,
                    approval.approval_id,
                ),
            )
        self._update_action_from_approval(approval)
        self.audit.record(
            category="actions",
            operation="approve",
            project_id=action.project_id,
            outcome="success",
            metadata={"action_id": action.action_id, "approval_id": approval.approval_id},
        )
        return approval

    def execute_action(self, action_id: str, *, confirmation_token: str, operator: str = "manual") -> tuple[OutputAction, ExecutionReceiptRecord]:
        action = self.get_action(action_id)
        if confirmation_token != action.action_id:
            raise PermissionDeniedError("Execution confirmation token mismatch.")
        if action.status not in {"approved", "awaiting_approval"}:
            raise PermissionDeniedError("Action is not approved.")
        approval = self.approval_for_action(action_id)
        if approval is None or approval.status != "approved_for_manual_use":
            raise PermissionDeniedError("A valid approved binding is required before execution.")
        if approval.expiry_timestamp and approval.expiry_timestamp < utc_now():
            raise PermissionDeniedError("Approval has expired.")
        if approval.approval_binding_hash != action.approval_binding_hash:
            raise PermissionDeniedError("Approval binding no longer matches the action.")
        manifest = self.get_permission_manifest(action.manifest_id)
        if manifest.manifest_version != action.manifest_version or not manifest.enabled:
            raise PermissionDeniedError("Permission manifest changed or is disabled.")
        target = (self.repo_root / action.canonical_target).resolve(strict=False)
        current_content, current_hash = self._load_existing_target(target)
        if action.previous_content_hash is not None and current_hash != action.previous_content_hash:
            action.status = "invalidated"
            action.denial_reason = "Target file changed unexpectedly."
            self._write_action(action)
            raise PermissionDeniedError("Target file changed unexpectedly.")
        if current_content is not None and manifest.overwrite_policy == "deny":
            raise PermissionDeniedError("Overwrite policy denies replacing an existing file.")
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_path: Path | None = None
        if current_content is not None:
            backup_dir = self.workspace_root / "backups" / action.action_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{target.name}.{utc_now().strftime('%Y%m%d%H%M%S')}.bak"
            shutil.copy2(target, backup_path)
            backup_hash = _hash_file(backup_path)
            backup_record = BackupRecord(
                action_id=action.action_id,
                target_path=_relative_display(target, self.repo_root),
                backup_path=_relative_display(backup_path, self.repo_root),
                content_hash=backup_hash,
                verified=True,
            )
            self._write_backup(backup_record)
        proposed_content = self._content_for_action(action)
        tmp_path = target.with_name(f"{target.name}.tmp-{uuid4().hex}")
        try:
            tmp_path.write_text(proposed_content, encoding="utf-8", newline="\n")
            os.replace(tmp_path, target)
        except Exception as exc:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            action.status = "failed"
            action.denial_reason = str(exc)
            self._write_action(action)
            self.audit.record(
                category="actions",
                operation="execute",
                project_id=action.project_id,
                outcome="failure",
                metadata={"action_id": action.action_id, "error": str(exc)},
                error_classification=type(exc).__name__,
            )
            raise
        resulting_hash = _hash_file(target)
        if resulting_hash != action.proposed_content_hash:
            action.status = "failed"
            action.denial_reason = "Resulting content hash mismatch."
            self._write_action(action)
            raise PermissionDeniedError("Resulting content hash mismatch.")
        receipt = ExecutionReceiptRecord(
            action_id=action.action_id,
            approval_id=approval.approval_id,
            manifest_id=manifest.manifest_id,
            manifest_version=manifest.manifest_version,
            source_draft_id=action.source_draft_id,
            source_draft_revision=action.source_draft_revision,
            target_path=_relative_display(target, self.repo_root),
            previous_hash=current_hash,
            resulting_hash=resulting_hash,
            backup_path=_relative_display(backup_path, self.repo_root) if backup_path else None,
            operator=operator,
            warnings=action.warnings,
            rollback_available=backup_path is not None and manifest.rollback_requirement,
        )
        self._write_receipt(receipt)
        action.execution_receipt_id = receipt.receipt_id
        action.execution_time = receipt.timestamp
        action.status = "completed"
        action.operator = operator
        action.backup_path = receipt.backup_path
        action.rollback_available = receipt.rollback_available
        action.result = receipt.result
        self._write_action(action)
        self.audit.record(
            category="actions",
            operation="execute",
            project_id=action.project_id,
            outcome="success",
            metadata={"action_id": action.action_id, "receipt_id": receipt.receipt_id},
        )
        return action, receipt

    def _content_for_action(self, action: OutputAction) -> str:
        if action.action_type == "rollback_output_file":
            if not action.backup_path:
                raise OutputWorkspaceError("Rollback action is missing a backup path.")
            backup = self._resolve_existing_path(action.backup_path)
            return backup.read_text(encoding="utf-8")
        if action.action_type == "export_draft":
            if not action.source_draft_id:
                raise OutputWorkspaceError("Draft export requires a source draft.")
            draft = self.workflow_service.get_draft(action.source_draft_id)
            revisions = self.workflow_service.draft_revisions(draft.draft_id)
            return revisions[-1].content if revisions else ""
        if action.action_type == "export_report":
            return self.project_service.foundation_report(action.project_id, "markdown")
        if action.action_type == "export_daily_brief":
            brief = self.workflow_service.briefs_latest(action.project_id) or self.workflow_service.daily_brief(action.project_id)
            return brief.markdown
        if action.action_type == "create_output_file":
            return action.proposed_content
        if action.action_type == "update_output_file":
            return action.proposed_content
        if action.action_type == "create_generated_document":
            return action.proposed_content
        raise OutputWorkspaceError("Unsupported action type.")

    def _resolve_existing_path(self, relative_path: str) -> Path:
        resolved = (self.repo_root / relative_path).resolve(strict=True)
        if self.repo_root not in resolved.parents and resolved != self.repo_root:
            raise PathSafetyError("Path escapes the GAIA repository.")
        return resolved

    def _write_receipt(self, receipt: ExecutionReceiptRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT INTO execution_receipts(
                    receipt_id, action_id, approval_id, manifest_id, manifest_version,
                    source_draft_id, source_draft_revision, target_path, previous_hash,
                    resulting_hash, backup_path, timestamp, operator, result, warnings_json,
                    rollback_available
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt.receipt_id,
                    receipt.action_id,
                    receipt.approval_id,
                    receipt.manifest_id,
                    receipt.manifest_version,
                    receipt.source_draft_id,
                    receipt.source_draft_revision,
                    receipt.target_path,
                    receipt.previous_hash,
                    receipt.resulting_hash,
                    receipt.backup_path,
                    receipt.timestamp.isoformat(),
                    receipt.operator,
                    receipt.result,
                    _json_dumps(receipt.warnings),
                    int(receipt.rollback_available),
                ),
            )

    def _write_backup(self, backup: BackupRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT INTO output_backups(
                    backup_id, action_id, target_path, backup_path, content_hash, created_at, verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    backup.backup_id,
                    backup.action_id,
                    backup.target_path,
                    backup.backup_path,
                    backup.content_hash,
                    backup.created_at.isoformat(),
                    int(backup.verified),
                ),
            )

    def _write_rollback(self, rollback: RollbackRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO rollback_records(
                    rollback_id, action_id, receipt_id, target_path, backup_path, previous_hash,
                    resulting_hash, created_at, executed_at, status, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rollback.rollback_id,
                    rollback.action_id,
                    rollback.receipt_id,
                    rollback.target_path,
                    rollback.backup_path,
                    rollback.previous_hash,
                    rollback.resulting_hash,
                    rollback.created_at.isoformat(),
                    rollback.executed_at.isoformat() if rollback.executed_at else None,
                    rollback.status,
                    rollback.reason,
                ),
            )

    def list_receipts(self, *, limit: int = 100, offset: int = 0) -> list[ExecutionReceiptRecord]:
        rows = self.database.connection.execute(
            "SELECT * FROM execution_receipts ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (max(1, min(limit, 500)), max(0, offset)),
        ).fetchall()
        receipts: list[ExecutionReceiptRecord] = []
        for row in rows:
            data = dict(row)
            data["timestamp"] = datetime.fromisoformat(str(data["timestamp"]))
            data["warnings"] = _json_loads(data.pop("warnings_json"), [])
            receipts.append(ExecutionReceiptRecord.model_validate(data))
        return receipts

    def get_receipt(self, receipt_id: str) -> ExecutionReceiptRecord:
        row = self.database.connection.execute(
            "SELECT * FROM execution_receipts WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        if not row:
            raise OutputWorkspaceError(f"Receipt not found: {receipt_id}")
        data = dict(row)
        data["timestamp"] = datetime.fromisoformat(str(data["timestamp"]))
        data["warnings"] = _json_loads(data.pop("warnings_json"), [])
        return ExecutionReceiptRecord.model_validate(data)

    def rollback_action(self, action_id: str, *, confirmation_token: str, operator: str = "manual") -> tuple[OutputAction, RollbackRecord]:
        action = self.get_action(action_id)
        if confirmation_token != action.action_id:
            raise PermissionDeniedError("Rollback confirmation token mismatch.")
        receipt = self.get_receipt(action.execution_receipt_id) if action.execution_receipt_id else None
        if not receipt or not receipt.rollback_available:
            raise PermissionDeniedError("Rollback is not available for this action.")
        rollback_path = self._resolve_existing_path(receipt.backup_path) if receipt.backup_path else None
        target_path = self._resolve_existing_path(receipt.target_path)
        if rollback_path is None:
            raise PermissionDeniedError("Rollback backup path is missing.")
        previous_hash = _hash_file(target_path) if target_path.exists() else None
        resulting_hash = _hash_file(rollback_path)
        shutil.copy2(rollback_path, target_path)
        action.status = "rolled_back"
        action.execution_time = utc_now()
        rollback = RollbackRecord(
            action_id=action.action_id,
            receipt_id=receipt.receipt_id,
            target_path=receipt.target_path,
            backup_path=receipt.backup_path or "",
            previous_hash=previous_hash,
            resulting_hash=resulting_hash,
            executed_at=utc_now(),
            status="executed",
            reason="Rolled back by operator",
        )
        self._write_rollback(rollback)
        self._write_action(action)
        self.audit.record(
            category="actions",
            operation="rollback",
            project_id=action.project_id,
            outcome="success",
            metadata={"action_id": action.action_id, "rollback_id": rollback.rollback_id},
        )
        return action, rollback

    def cancel_action(self, action_id: str, reason: str = "cancelled") -> OutputAction:
        action = self.get_action(action_id)
        action.status = "cancelled"
        action.denial_reason = reason
        self._write_action(action)
        self.audit.record(
            category="actions",
            operation="cancel",
            project_id=action.project_id,
            outcome="success",
            metadata={"action_id": action.action_id, "reason": reason},
        )
        return action

    # ------------------------------------------------------------------
    # Summaries and helpers
    # ------------------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        manifests = self.list_permission_manifests()
        actions = self.list_actions(limit=500)
        receipts = self.list_receipts(limit=500)
        return {
            "status": "ok",
            "manifest_count": len(manifests),
            "enabled_manifest_count": sum(manifest.enabled for manifest in manifests),
            "action_count": len(actions),
            "receipt_count": len(receipts),
            "workspace_root": str(self.workspace_root),
        }
