from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from typing import Any, Literal, cast
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from gaia.audit import AuditRecorder
from gaia.config import Settings
from gaia.db import Database
from gaia.models import utc_now
from gaia.service import ProjectService

TaskStatus = Literal[
    "proposed",
    "backlog",
    "ready",
    "in_progress",
    "blocked",
    "awaiting_approval",
    "completed",
    "cancelled",
]
TaskPriority = Literal["low", "normal", "high", "critical"]
DraftType = Literal[
    "codex_prompt",
    "project_report",
    "user_guide",
    "release_note",
    "task_plan",
    "meeting_brief",
    "communication",
    "daily_brief",
    "generic_markdown",
]
DraftStatus = Literal["working", "ready_for_review", "approved_for_manual_use", "rejected", "superseded"]
ApprovalStatus = Literal["pending", "approved_for_manual_use", "rejected", "expired", "cancelled", "invalidated"]
ApprovalRisk = Literal["low", "medium", "high", "prohibited"]

TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    "proposed": {"backlog", "cancelled"},
    "backlog": {"ready", "cancelled"},
    "ready": {"in_progress", "cancelled"},
    "in_progress": {"blocked", "awaiting_approval", "cancelled"},
    "blocked": {"ready", "cancelled"},
    "awaiting_approval": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
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
    if not str(value).strip():
        return default
    return json.loads(str(value))


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class TaskRecord(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    project_id: str
    status: TaskStatus = "proposed"
    priority: TaskPriority = "normal"
    category: str = "general"
    source_type: str = "manual"
    source_identifier: str | None = None
    source_agent_run_id: str | None = None
    evidence_references: list[str] = Field(default_factory=list)
    dependency_task_ids: list[str] = Field(default_factory=list)
    blocker_description: str | None = None
    assigned_to: str | None = None
    due_date: datetime | None = None
    completion_criteria: str = ""
    completion_evidence: list[str] = Field(default_factory=list)
    approval_requirement: bool = False
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    version: int = 1
    manual_override_reason: str | None = None

    @field_validator("title", "description", "category", "source_type", "completion_criteria", "assigned_to", "blocker_description", "manual_override_reason")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class TaskHistoryRecord(BaseModel):
    history_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    from_status: str | None = None
    to_status: str
    action: str
    actor: str
    reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    project_id: str = Field(min_length=1, max_length=100)
    priority: TaskPriority = "normal"
    category: str = "general"
    source_type: str = "manual"
    source_identifier: str | None = None
    source_agent_run_id: str | None = None
    evidence_references: list[str] = Field(default_factory=list)
    dependency_task_ids: list[str] = Field(default_factory=list)
    blocker_description: str | None = None
    assigned_to: str | None = None
    due_date: datetime | None = None
    completion_criteria: str = ""
    completion_evidence: list[str] = Field(default_factory=list)
    approval_requirement: bool = False
    tags: list[str] = Field(default_factory=list)
    status: TaskStatus = "proposed"


class TaskUpdateRequest(BaseModel):
    version: int
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    priority: TaskPriority | None = None
    category: str | None = None
    assigned_to: str | None = None
    blocker_description: str | None = None
    due_date: datetime | None = None
    completion_criteria: str | None = None
    completion_evidence: list[str] | None = None
    approval_requirement: bool | None = None
    tags: list[str] | None = None
    evidence_references: list[str] | None = None
    dependency_task_ids: list[str] | None = None


class TaskTransitionRequest(BaseModel):
    version: int
    status: TaskStatus
    reason: str | None = None
    completion_evidence: list[str] | None = None
    manual_override_reason: str | None = None
    blocker_description: str | None = None
    assigned_to: str | None = None
    actor: str = "manual"


class DraftRecord(BaseModel):
    draft_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(min_length=1, max_length=200)
    draft_type: DraftType = "generic_markdown"
    project_id: str
    source_task_id: str | None = None
    source_agent_run_id: str | None = None
    current_revision: int = 1
    current_content_hash: str
    status: DraftStatus = "working"
    evidence_references: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    approval_requirement: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DraftRevisionRecord(BaseModel):
    revision_id: str = Field(default_factory=lambda: str(uuid4()))
    draft_id: str
    revision_number: int
    content: str
    content_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    author: str = "manual"
    change_reason: str = ""


class DraftCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    draft_type: DraftType = "generic_markdown"
    project_id: str
    source_task_id: str | None = None
    source_agent_run_id: str | None = None
    content: str = ""
    evidence_references: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    approval_requirement: bool = False
    author: str = "manual"
    change_reason: str = "initial draft"
    status: DraftStatus = "working"


class DraftReviseRequest(BaseModel):
    version: int
    content: str
    author: str = "manual"
    change_reason: str = "revision"
    warnings: list[str] | None = None
    evidence_references: list[str] | None = None
    status: DraftStatus | None = None


class ApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    request_type: str = "manual"
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    project_id: str
    source_task_id: str | None = None
    source_draft_id: str | None = None
    requesting_source: str = "manual"
    proposed_action: str = ""
    exact_target_description: str = ""
    write_boundary: str = "gaia-local"
    risk_level: ApprovalRisk = "low"
    preview_summary: str = ""
    approved_content_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    expiry_timestamp: datetime | None = None
    status: ApprovalStatus = "pending"
    reviewer: str | None = None
    decision_timestamp: datetime | None = None
    decision_reason: str | None = None
    audit_references: list[str] = Field(default_factory=list)
    invalidation_reason: str | None = None
    version: int = 1


class ApprovalCreateRequest(BaseModel):
    request_type: str = "manual"
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    project_id: str
    source_task_id: str | None = None
    source_draft_id: str | None = None
    requesting_source: str = "manual"
    proposed_action: str = ""
    exact_target_description: str = ""
    write_boundary: str = "gaia-local"
    risk_level: ApprovalRisk = "low"
    preview_summary: str = ""
    approved_content_hash: str = ""
    expiry_timestamp: datetime | None = None
    reviewer: str | None = None
    audit_references: list[str] = Field(default_factory=list)


class ApprovalDecisionRequest(BaseModel):
    version: int
    reviewer: str = "manual"
    decision_reason: str = ""


class DailyBriefRecord(BaseModel):
    brief_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    title: str
    created_at: datetime = Field(default_factory=utc_now)
    repository_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    verified_facts: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    markdown: str = ""
    source_task_ids: list[str] = Field(default_factory=list)
    source_approval_ids: list[str] = Field(default_factory=list)
    source_run_ids: list[str] = Field(default_factory=list)


class WorkflowError(Exception):
    pass


class NotFoundError(WorkflowError):
    pass


class ConflictError(WorkflowError):
    pass


class ValidationError(WorkflowError):
    pass


class TaskWorkflowService:
    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.project_service = ProjectService(settings, self.database)
        self.audit = AuditRecorder(self.database)

    def close(self) -> None:
        self.database.close()

    def _project_exists(self, project_id: str) -> None:
        self.project_service.get_project(project_id)

    def _run_row(self, run_id: str) -> dict[str, Any]:
        run = self.database.get_agent_run(run_id)
        if not run:
            raise NotFoundError(f"Run not found: {run_id}")
        return run

    def _task_row(self, task_id: str) -> sqlite3.Row:
        row = cast(
            sqlite3.Row | None,
            self.database.connection.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone(),
        )
        if not row:
            raise NotFoundError(f"Task not found: {task_id}")
        return row

    def _draft_row(self, draft_id: str) -> sqlite3.Row:
        row = cast(
            sqlite3.Row | None,
            self.database.connection.execute("SELECT * FROM drafts WHERE draft_id = ?", (draft_id,)).fetchone(),
        )
        if not row:
            raise NotFoundError(f"Draft not found: {draft_id}")
        return row

    def _approval_row(self, approval_id: str) -> sqlite3.Row:
        row = cast(
            sqlite3.Row | None,
            self.database.connection.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone(),
        )
        if not row:
            raise NotFoundError(f"Approval not found: {approval_id}")
        return row

    def _brief_row(self, brief_id: str) -> sqlite3.Row:
        row = cast(
            sqlite3.Row | None,
            self.database.connection.execute("SELECT * FROM daily_briefs WHERE brief_id = ?", (brief_id,)).fetchone(),
        )
        if not row:
            raise NotFoundError(f"Brief not found: {brief_id}")
        return row

    def _task_from_row(self, row: sqlite3.Row) -> TaskRecord:
        data = dict(row)
        data["evidence_references"] = _json_loads(data.pop("evidence_references_json"), [])
        data["dependency_task_ids"] = _json_loads(data.pop("dependency_task_ids_json"), [])
        data["completion_evidence"] = _json_loads(data.pop("completion_evidence_json"), [])
        data["tags"] = _json_loads(data.pop("tags_json"), [])
        data["approval_requirement"] = bool(data.get("approval_requirement"))
        if data.get("due_date"):
            data["due_date"] = datetime.fromisoformat(str(data["due_date"]))
        data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
        data["updated_at"] = datetime.fromisoformat(str(data["updated_at"]))
        return TaskRecord.model_validate(data)

    def _task_history_from_row(self, row: sqlite3.Row) -> TaskHistoryRecord:
        data = dict(row)
        data["metadata"] = _json_loads(data.pop("metadata_json"), {})
        data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
        return TaskHistoryRecord.model_validate(data)

    def _draft_from_row(self, row: sqlite3.Row) -> DraftRecord:
        data = dict(row)
        data["evidence_references"] = _json_loads(data.pop("evidence_references_json"), [])
        data["warnings"] = _json_loads(data.pop("warnings_json"), [])
        data["approval_requirement"] = bool(data.get("approval_requirement"))
        data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
        data["updated_at"] = datetime.fromisoformat(str(data["updated_at"]))
        return DraftRecord.model_validate(data)

    def _revision_from_row(self, row: sqlite3.Row) -> DraftRevisionRecord:
        data = dict(row)
        data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
        return DraftRevisionRecord.model_validate(data)

    def _approval_from_row(self, row: sqlite3.Row) -> ApprovalRecord:
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

    def _brief_from_row(self, row: sqlite3.Row) -> DailyBriefRecord:
        data = dict(row)
        data["repository_snapshot_json"] = _json_loads(data.pop("repository_snapshot_json"), {})
        data["verified_facts"] = _json_loads(data.pop("verified_facts_json"), [])
        data["inferences"] = _json_loads(data.pop("inferences_json"), [])
        data["recommendations"] = _json_loads(data.pop("recommendations_json"), [])
        data["warnings"] = _json_loads(data.pop("warnings_json"), [])
        data["unknowns"] = _json_loads(data.pop("unknowns_json"), [])
        data["source_task_ids"] = _json_loads(data.pop("source_task_ids_json"), [])
        data["source_approval_ids"] = _json_loads(data.pop("source_approval_ids_json"), [])
        data["source_run_ids"] = _json_loads(data.pop("source_run_ids_json"), [])
        data["created_at"] = datetime.fromisoformat(str(data["created_at"]))
        return DailyBriefRecord.model_validate(data)

    def _write_task(self, task: TaskRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO tasks(
                    task_id, title, description, project_id, status, priority, category,
                    source_type, source_identifier, source_agent_run_id, evidence_references_json,
                    dependency_task_ids_json, blocker_description, assigned_to, due_date,
                    completion_criteria, completion_evidence_json, approval_requirement,
                    tags_json, created_at, updated_at, version, manual_override_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.title,
                    task.description,
                    task.project_id,
                    task.status,
                    task.priority,
                    task.category,
                    task.source_type,
                    task.source_identifier,
                    task.source_agent_run_id,
                    _json_dumps(task.evidence_references),
                    _json_dumps(task.dependency_task_ids),
                    task.blocker_description,
                    task.assigned_to,
                    task.due_date.isoformat() if task.due_date else None,
                    task.completion_criteria,
                    _json_dumps(task.completion_evidence),
                    int(task.approval_requirement),
                    _json_dumps(task.tags),
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    task.version,
                    task.manual_override_reason,
                ),
            )

    def _write_task_history(self, history: TaskHistoryRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT INTO task_history(
                    history_id, task_id, from_status, to_status, action, actor, reason, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history.history_id,
                    history.task_id,
                    history.from_status,
                    history.to_status,
                    history.action,
                    history.actor,
                    history.reason,
                    history.created_at.isoformat(),
                    _json_dumps(history.metadata),
                ),
            )

    def _write_draft(self, draft: DraftRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO drafts(
                    draft_id, title, draft_type, project_id, source_task_id, source_agent_run_id,
                    current_revision, current_content_hash, status, evidence_references_json,
                    warnings_json, approval_requirement, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft.draft_id,
                    draft.title,
                    draft.draft_type,
                    draft.project_id,
                    draft.source_task_id,
                    draft.source_agent_run_id,
                    draft.current_revision,
                    draft.current_content_hash,
                    draft.status,
                    _json_dumps(draft.evidence_references),
                    _json_dumps(draft.warnings),
                    int(draft.approval_requirement),
                    draft.created_at.isoformat(),
                    draft.updated_at.isoformat(),
                ),
            )

    def _write_revision(self, revision: DraftRevisionRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT INTO draft_revisions(
                    revision_id, draft_id, revision_number, content, content_hash, created_at, author, change_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.draft_id,
                    revision.revision_number,
                    revision.content,
                    revision.content_hash,
                    revision.created_at.isoformat(),
                    revision.author,
                    revision.change_reason,
                ),
            )

    def _write_approval(self, approval: ApprovalRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO approvals(
                    approval_id, request_type, title, description, project_id, source_task_id,
                    source_draft_id, requesting_source, proposed_action, exact_target_description,
                    write_boundary, risk_level, preview_summary, approved_content_hash, created_at,
                    expiry_timestamp, status, reviewer, decision_timestamp, decision_reason,
                    audit_references_json, invalidation_reason, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )

    def _write_brief(self, brief: DailyBriefRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO daily_briefs(
                    brief_id, project_id, title, created_at, repository_snapshot_json,
                    verified_facts_json, inferences_json, recommendations_json, warnings_json,
                    unknowns_json, markdown, source_task_ids_json, source_approval_ids_json, source_run_ids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brief.brief_id,
                    brief.project_id,
                    brief.title,
                    brief.created_at.isoformat(),
                    _json_dumps(brief.repository_snapshot_json),
                    _json_dumps(brief.verified_facts),
                    _json_dumps(brief.inferences),
                    _json_dumps(brief.recommendations),
                    _json_dumps(brief.warnings),
                    _json_dumps(brief.unknowns),
                    brief.markdown,
                    _json_dumps(brief.source_task_ids),
                    _json_dumps(brief.source_approval_ids),
                    _json_dumps(brief.source_run_ids),
                ),
            )

    def create_task(self, request: TaskCreateRequest) -> TaskRecord:
        self._project_exists(request.project_id)
        if request.status == "completed" and not request.completion_evidence:
            raise ValidationError("Completed tasks require completion evidence or a manual override reason.")
        if request.status not in TASK_TRANSITIONS:
            raise ValidationError(f"Invalid task status: {request.status}")
        if request.source_type == "agent_run" and request.status != "proposed":
            raise ValidationError("Agent-run tasks must start in proposed status.")
        if request.status == "proposed" and request.source_type == "agent_run" and not request.source_agent_run_id:
            raise ValidationError("Agent-run tasks require a source agent run ID.")
        task = TaskRecord(
            title=request.title,
            description=request.description,
            project_id=request.project_id,
            status=request.status,
            priority=request.priority,
            category=request.category,
            source_type=request.source_type,
            source_identifier=request.source_identifier or request.source_agent_run_id,
            source_agent_run_id=request.source_agent_run_id,
            evidence_references=request.evidence_references,
            dependency_task_ids=request.dependency_task_ids,
            blocker_description=request.blocker_description,
            assigned_to=request.assigned_to,
            due_date=request.due_date,
            completion_criteria=request.completion_criteria,
            completion_evidence=request.completion_evidence,
            approval_requirement=request.approval_requirement,
            tags=request.tags,
        )
        self._write_task(task)
        self._write_task_history(
            TaskHistoryRecord(
                task_id=task.task_id,
                from_status=None,
                to_status=task.status,
                action="create",
                actor=task.source_type,
                metadata={"source_identifier": task.source_identifier, "version": task.version},
            )
        )
        self.audit.record(
            category="tasks",
            operation="create",
            project_id=task.project_id,
            outcome="success",
            metadata={"task_id": task.task_id, "status": task.status},
        )
        return task

    def list_tasks(
        self,
        *,
        project_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TaskRecord]:
        clauses = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if priority:
            clauses.append("priority = ?")
            params.append(priority)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.connection.execute(
            f"SELECT * FROM tasks {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (*params, max(1, min(limit, 500)), max(0, offset)),
        ).fetchall()
        return [self._task_from_row(row) for row in rows]

    def get_task(self, task_id: str) -> TaskRecord:
        return self._task_from_row(self._task_row(task_id))

    def update_task(self, task_id: str, request: TaskUpdateRequest) -> TaskRecord:
        task = self.get_task(task_id)
        if task.version != request.version:
            raise ConflictError("Task version mismatch.")
        updates = request.model_dump(exclude={"version"}, exclude_none=True)
        for key, value in updates.items():
            if key == "title":
                task.title = str(value)
            elif key == "description":
                task.description = str(value)
            elif key == "priority":
                task.priority = cast(TaskPriority, value)
            elif key == "category":
                task.category = str(value)
            elif key == "assigned_to":
                task.assigned_to = str(value)
            elif key == "blocker_description":
                task.blocker_description = str(value)
            elif key == "due_date":
                task.due_date = value
            elif key == "completion_criteria":
                task.completion_criteria = str(value)
            elif key == "completion_evidence":
                task.completion_evidence = list(value)
            elif key == "approval_requirement":
                task.approval_requirement = bool(value)
            elif key == "tags":
                task.tags = list(value)
            elif key == "evidence_references":
                task.evidence_references = list(value)
            elif key == "dependency_task_ids":
                task.dependency_task_ids = list(value)
        if task.status == "completed" and not (task.completion_evidence or task.manual_override_reason):
            raise ValidationError("Completed tasks require completion evidence or a manual override reason.")
        task.version += 1
        task.updated_at = utc_now()
        self._write_task(task)
        self._write_task_history(
            TaskHistoryRecord(
                task_id=task.task_id,
                from_status=task.status,
                to_status=task.status,
                action="update",
                actor="manual",
                metadata={"version": task.version},
            )
        )
        self.audit.record(
            category="tasks",
            operation="update",
            project_id=task.project_id,
            outcome="success",
            metadata={"task_id": task.task_id, "version": task.version},
        )
        return task

    def transition_task(self, task_id: str, request: TaskTransitionRequest) -> TaskRecord:
        task = self.get_task(task_id)
        if task.version != request.version:
            raise ConflictError("Task version mismatch.")
        previous_status = task.status
        allowed = TASK_TRANSITIONS[task.status]
        if request.status not in allowed:
            raise ValidationError(f"Transition {task.status} -> {request.status} is not permitted.")
        if request.status == "completed" and not (request.completion_evidence or request.manual_override_reason):
            raise ValidationError("Completion requires evidence or a manual override reason.")
        if request.status == "completed":
            task.completion_evidence = request.completion_evidence or task.completion_evidence
            task.manual_override_reason = request.manual_override_reason
        if request.blocker_description is not None:
            task.blocker_description = request.blocker_description
        if request.assigned_to is not None:
            task.assigned_to = request.assigned_to
        task.status = request.status
        task.version += 1
        task.updated_at = utc_now()
        self._write_task(task)
        self._write_task_history(
            TaskHistoryRecord(
                task_id=task.task_id,
                from_status=previous_status,
                to_status=task.status,
                action="transition",
                actor=request.actor,
                reason=request.reason,
                metadata={
                    "version": task.version,
                    "completion_evidence": request.completion_evidence or [],
                    "manual_override_reason": request.manual_override_reason,
                },
            )
        )
        self.audit.record(
            category="tasks",
            operation="transition",
            project_id=task.project_id,
            outcome="success",
            metadata={"task_id": task.task_id, "from_status": previous_status, "to_status": request.status},
        )
        return task

    def accept_task(self, task_id: str, *, actor: str = "manual") -> TaskRecord:
        task = self.get_task(task_id)
        if task.status != "proposed":
            raise ValidationError("Only proposed tasks can be accepted.")
        return self.transition_task(
            task_id,
            TaskTransitionRequest(version=task.version, status="backlog", actor=actor, reason="accepted"),
        )

    def cancel_task(self, task_id: str, *, reason: str | None = None, actor: str = "manual") -> TaskRecord:
        task = self.get_task(task_id)
        if task.status == "completed":
            raise ValidationError("Completed tasks cannot be cancelled.")
        return self.transition_task(
            task_id,
            TaskTransitionRequest(version=task.version, status="cancelled", actor=actor, reason=reason),
        )

    def task_history(self, task_id: str) -> list[TaskHistoryRecord]:
        rows = self.database.connection.execute(
            "SELECT * FROM task_history WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        ).fetchall()
        return [self._task_history_from_row(row) for row in rows]

    def create_task_from_run(self, run_id: str) -> TaskRecord:
        run = self._run_row(run_id)
        return self.create_task(
            TaskCreateRequest(
                title=str(run["question"])[:200],
                description=str(run["structured_answer"]),
                project_id=str(run["project_id"]),
                priority="normal",
                category=str(run["question_category"]),
                source_type="agent_run",
                source_identifier=run_id,
                source_agent_run_id=run_id,
                evidence_references=[
                    str(item.get("source_path", ""))
                    for item in _json_loads(run.get("selected_evidence", []), [])
                    if isinstance(item, dict)
                ],
                approval_requirement=True,
                status="proposed",
                tags=["agent-run", "proposed"],
            )
        )

    def create_draft(self, request: DraftCreateRequest) -> tuple[DraftRecord, DraftRevisionRecord]:
        self._project_exists(request.project_id)
        content = self._ensure_codex_marker(request.draft_type, request.content)
        content_hash = _hash_content(content)
        draft = DraftRecord(
            title=request.title,
            draft_type=request.draft_type,
            project_id=request.project_id,
            source_task_id=request.source_task_id,
            source_agent_run_id=request.source_agent_run_id,
            current_revision=1,
            current_content_hash=content_hash,
            status=request.status,
            evidence_references=request.evidence_references,
            warnings=request.warnings,
            approval_requirement=request.approval_requirement,
        )
        revision = DraftRevisionRecord(
            draft_id=draft.draft_id,
            revision_number=1,
            content=content,
            content_hash=content_hash,
            author=request.author,
            change_reason=request.change_reason,
        )
        self._write_draft(draft)
        self._write_revision(revision)
        self.audit.record(
            category="drafts",
            operation="create",
            project_id=draft.project_id,
            outcome="success",
            metadata={"draft_id": draft.draft_id, "revision": 1, "content_hash": content_hash},
        )
        return draft, revision

    def list_drafts(self, *, project_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0) -> list[DraftRecord]:
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
            f"SELECT * FROM drafts {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (*params, max(1, min(limit, 500)), max(0, offset)),
        ).fetchall()
        return [self._draft_from_row(row) for row in rows]

    def get_draft(self, draft_id: str) -> DraftRecord:
        return self._draft_from_row(self._draft_row(draft_id))

    def draft_revisions(self, draft_id: str) -> list[DraftRevisionRecord]:
        rows = self.database.connection.execute(
            "SELECT * FROM draft_revisions WHERE draft_id = ? ORDER BY revision_number ASC",
            (draft_id,),
        ).fetchall()
        return [self._revision_from_row(row) for row in rows]

    def revise_draft(self, draft_id: str, request: DraftReviseRequest) -> tuple[DraftRecord, DraftRevisionRecord]:
        draft = self.get_draft(draft_id)
        if draft.current_revision != request.version:
            raise ConflictError("Draft version mismatch.")
        content = self._ensure_codex_marker(draft.draft_type, request.content)
        content_hash = _hash_content(content)
        draft.current_revision += 1
        draft.current_content_hash = content_hash
        draft.updated_at = utc_now()
        if request.status is not None:
            draft.status = request.status
        if request.warnings is not None:
            draft.warnings = request.warnings
        if request.evidence_references is not None:
            draft.evidence_references = request.evidence_references
        self._write_draft(draft)
        revision = DraftRevisionRecord(
            draft_id=draft.draft_id,
            revision_number=draft.current_revision,
            content=content,
            content_hash=content_hash,
            author=request.author,
            change_reason=request.change_reason,
        )
        self._write_revision(revision)
        self._invalidate_approvals_for_draft(draft.draft_id, content_hash)
        self.audit.record(
            category="drafts",
            operation="revise",
            project_id=draft.project_id,
            outcome="success",
            metadata={"draft_id": draft.draft_id, "revision": draft.current_revision},
        )
        return draft, revision

    def submit_draft_for_review(self, draft_id: str) -> DraftRecord:
        draft = self.get_draft(draft_id)
        draft.status = "ready_for_review"
        draft.updated_at = utc_now()
        self._write_draft(draft)
        self.audit.record(category="drafts", operation="submit_for_review", project_id=draft.project_id, outcome="success", metadata={"draft_id": draft.draft_id})
        return draft

    def reject_draft(self, draft_id: str) -> DraftRecord:
        draft = self.get_draft(draft_id)
        draft.status = "rejected"
        draft.updated_at = utc_now()
        self._write_draft(draft)
        self.audit.record(category="drafts", operation="reject", project_id=draft.project_id, outcome="success", metadata={"draft_id": draft.draft_id})
        return draft

    def supersede_draft(self, draft_id: str) -> DraftRecord:
        draft = self.get_draft(draft_id)
        draft.status = "superseded"
        draft.updated_at = utc_now()
        self._write_draft(draft)
        self.audit.record(category="drafts", operation="supersede", project_id=draft.project_id, outcome="success", metadata={"draft_id": draft.draft_id})
        return draft

    def create_approval(self, request: ApprovalCreateRequest) -> ApprovalRecord:
        self._project_exists(request.project_id)
        if request.risk_level == "prohibited":
            raise ValidationError("Prohibited actions cannot be approved.")
        if request.source_draft_id:
            draft = self.get_draft(request.source_draft_id)
            if request.approved_content_hash and request.approved_content_hash != draft.current_content_hash:
                raise ValidationError("Approval hash does not match the current draft.")
            approved_hash = request.approved_content_hash or draft.current_content_hash
        else:
            approved_hash = request.approved_content_hash
        approval = ApprovalRecord(
            request_type=request.request_type,
            title=request.title,
            description=request.description,
            project_id=request.project_id,
            source_task_id=request.source_task_id,
            source_draft_id=request.source_draft_id,
            requesting_source=request.requesting_source,
            proposed_action=request.proposed_action,
            exact_target_description=request.exact_target_description,
            write_boundary=request.write_boundary,
            risk_level=request.risk_level,
            preview_summary=request.preview_summary,
            approved_content_hash=approved_hash,
            expiry_timestamp=request.expiry_timestamp,
            reviewer=request.reviewer,
        )
        self._write_approval(approval)
        self.audit.record(category="approvals", operation="create", project_id=approval.project_id, outcome="success", metadata={"approval_id": approval.approval_id, "risk_level": approval.risk_level})
        return approval

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

    def get_approval(self, approval_id: str) -> ApprovalRecord:
        return self._approval_from_row(self._approval_row(approval_id))

    def approve(self, approval_id: str, request: ApprovalDecisionRequest) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if approval.version != request.version:
            raise ConflictError("Approval version mismatch.")
        self._validate_approval_decision(approval, request)
        approval.status = "approved_for_manual_use"
        approval.reviewer = request.reviewer
        approval.decision_timestamp = utc_now()
        approval.decision_reason = request.decision_reason
        approval.version += 1
        self._write_approval(approval)
        self.audit.record(category="approvals", operation="approve", project_id=approval.project_id, outcome="success", metadata={"approval_id": approval.approval_id, "status": approval.status})
        return approval

    def reject_approval(self, approval_id: str, request: ApprovalDecisionRequest) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if approval.version != request.version:
            raise ConflictError("Approval version mismatch.")
        if not request.decision_reason.strip():
            raise ValidationError("Rejected approvals require an explicit reason.")
        approval.status = "rejected"
        approval.reviewer = request.reviewer
        approval.decision_timestamp = utc_now()
        approval.decision_reason = request.decision_reason
        approval.version += 1
        self._write_approval(approval)
        self.audit.record(category="approvals", operation="reject", project_id=approval.project_id, outcome="success", metadata={"approval_id": approval.approval_id})
        return approval

    def cancel_approval(self, approval_id: str, request: ApprovalDecisionRequest) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if approval.version != request.version:
            raise ConflictError("Approval version mismatch.")
        approval.status = "cancelled"
        approval.reviewer = request.reviewer
        approval.decision_timestamp = utc_now()
        approval.decision_reason = request.decision_reason or "cancelled"
        approval.version += 1
        self._write_approval(approval)
        self.audit.record(category="approvals", operation="cancel", project_id=approval.project_id, outcome="success", metadata={"approval_id": approval.approval_id})
        return approval

    def refresh_approval_validation(self, approval_id: str) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if approval.expiry_timestamp and approval.expiry_timestamp < utc_now():
            approval.status = "expired"
            approval.decision_timestamp = utc_now()
            approval.invalidation_reason = "Approval expired."
            approval.version += 1
            self._write_approval(approval)
        elif approval.source_draft_id:
            draft = self.get_draft(approval.source_draft_id)
            if approval.approved_content_hash and approval.approved_content_hash != draft.current_content_hash:
                approval.status = "invalidated"
                approval.decision_timestamp = utc_now()
                approval.invalidation_reason = "Draft content changed."
                approval.version += 1
                self._write_approval(approval)
        self.audit.record(category="approvals", operation="refresh_validation", project_id=approval.project_id, outcome="success", metadata={"approval_id": approval.approval_id, "status": approval.status})
        return approval

    def _invalidate_approvals_for_draft(self, draft_id: str, content_hash: str) -> None:
        rows = self.database.connection.execute(
            "SELECT * FROM approvals WHERE source_draft_id = ?",
            (draft_id,),
        ).fetchall()
        for row in rows:
            approval = self._approval_from_row(row)
            if approval.approved_content_hash and approval.approved_content_hash != content_hash and approval.status == "approved_for_manual_use":
                approval.status = "invalidated"
                approval.invalidation_reason = "Draft content changed."
                approval.version += 1
                self._write_approval(approval)

    def _validate_approval_decision(self, approval: ApprovalRecord, request: ApprovalDecisionRequest) -> None:
        if approval.risk_level == "prohibited":
            raise ValidationError("Prohibited actions cannot be approved.")
        if approval.expiry_timestamp and approval.expiry_timestamp < utc_now():
            raise ValidationError("Expired approvals cannot be approved.")
        if approval.source_draft_id:
            draft = self.get_draft(approval.source_draft_id)
            if approval.approved_content_hash and approval.approved_content_hash != draft.current_content_hash:
                raise ValidationError("Approval hash is stale.")
        if (
            approval.requesting_source
            and approval.requesting_source.lower() != "manual"
            and approval.requesting_source.lower() == request.reviewer.lower()
        ):
            raise ValidationError("Models cannot approve their own output.")
        if approval.risk_level in {"high"} and not request.decision_reason.strip():
            raise ValidationError("High-risk approvals require an explicit decision reason.")
        if request.decision_reason.strip() == "" and approval.risk_level in {"medium", "high"}:
            raise ValidationError("Approval decision requires a reason.")

    def daily_brief(self, project_id: str) -> DailyBriefRecord:
        self._project_exists(project_id)
        project = self.project_service.get_project(project_id)
        snapshot = self.database.latest_snapshot(project_id)
        if snapshot is None:
            snapshot = self.project_service.snapshot(project_id)
        tasks = self.list_tasks(project_id=project_id, limit=200)
        approvals = self.list_approvals(project_id=project_id, limit=200)
        runs = [item for item in self.database.list_agent_runs(limit=50) if item["project_id"] == project_id]
        documents = self.database.list_documents(project_id)
        warnings = [str(row.get("warning")) for row in documents if row.get("warning")]
        verified_facts = [
            f"Project {project.project_id} rooted at {project.root}",
            f"Snapshot {snapshot.snapshot_id} captured at {snapshot.created_at.isoformat()}",
            f"{len(runs)} recent agent runs",
            f"{len(tasks)} tasks recorded",
            f"{len(approvals)} approvals recorded",
        ]
        proposed = [task.title for task in tasks if task.status in {"proposed", "backlog", "ready", "in_progress"}][:8]
        blocked = [task.title for task in tasks if task.status == "blocked"][:8]
        pending = [approval.title for approval in approvals if approval.status == "pending"][:8]
        docs_gaps = [path for path, exists in snapshot.important_paths.items() if not exists]
        recommendations = [
            "Review proposed tasks and move accepted items into backlog.",
            "Resolve blocked tasks before approving downstream drafts.",
            "Generate or refresh missing project documentation.",
        ]
        unknowns = [
            "Whether all pending approvals are still required.",
            "Whether the latest agent runs have been reviewed manually.",
        ]
        warning_lines = [f"- {item}" for item in warnings] or ["- None"]
        markdown = "\n".join(
            [
                "# Daily Operations Brief",
                "",
                "## Verified Facts",
                *[f"- {item}" for item in verified_facts],
                "",
                "## Inference",
                "- This brief is a deterministic summary of local GAIA records and Git state.",
                "",
                "## Recommendations",
                *[f"- {item}" for item in recommendations],
                "",
                "## Warnings",
                *warning_lines,
                "",
                "## Unknowns",
                *[f"- {item}" for item in unknowns],
            ]
        )
        brief = DailyBriefRecord(
            project_id=project_id,
            title=f"Daily Operations Brief - {project.project_id}",
            repository_snapshot_json=snapshot.model_dump(mode="json"),
            verified_facts=verified_facts,
            inferences=[
                f"Proposed/active tasks: {len(proposed)}",
                f"Blocked tasks: {len(blocked)}",
                f"Pending approvals: {len(pending)}",
                f"Documentation gaps: {len(docs_gaps)}",
            ],
            recommendations=recommendations,
            warnings=warnings,
            unknowns=unknowns + [f"Documentation gaps: {', '.join(docs_gaps) if docs_gaps else 'none'}"],
            markdown=markdown,
            source_task_ids=[task.task_id for task in tasks[:10]],
            source_approval_ids=[approval.approval_id for approval in approvals[:10]],
            source_run_ids=[str(run["run_id"]) for run in runs[:10]],
        )
        self._write_brief(brief)
        self.audit.record(category="briefs", operation="daily", project_id=project_id, outcome="success", metadata={"brief_id": brief.brief_id})
        return brief

    def list_briefs(self, *, project_id: str | None = None, limit: int = 100, offset: int = 0) -> list[DailyBriefRecord]:
        clauses = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.connection.execute(
            f"SELECT * FROM daily_briefs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, max(1, min(limit, 500)), max(0, offset)),
        ).fetchall()
        return [self._brief_from_row(row) for row in rows]

    def get_brief(self, brief_id: str) -> DailyBriefRecord:
        return self._brief_from_row(self._brief_row(brief_id))

    def integration_status(self) -> dict[str, Any]:
        import gaia

        projects = [project.model_dump(mode="json") for project in self.settings.projects.values()]
        return {
            "status": "ok",
            "backend_version": gaia.__version__,
            "projects": projects,
            "task_count": len(self.list_tasks(limit=500)),
            "approval_count": len(self.list_approvals(limit=500)),
            "brief_count": len(self.list_briefs(limit=500)),
        }

    def task_summary(self, project_id: str | None = None) -> dict[str, Any]:
        tasks = self.list_tasks(project_id=project_id, limit=500)
        return {
            "project_id": project_id,
            "total": len(tasks),
            "proposed": sum(task.status == "proposed" for task in tasks),
            "active": sum(task.status in {"backlog", "ready", "in_progress", "blocked", "awaiting_approval"} for task in tasks),
            "blocked": sum(task.status == "blocked" for task in tasks),
            "completed": sum(task.status == "completed" for task in tasks),
        }

    def approval_summary(self, project_id: str | None = None) -> dict[str, Any]:
        approvals = self.list_approvals(project_id=project_id, limit=500)
        return {
            "project_id": project_id,
            "total": len(approvals),
            "pending": sum(approval.status == "pending" for approval in approvals),
            "approved": sum(approval.status == "approved_for_manual_use" for approval in approvals),
            "rejected": sum(approval.status == "rejected" for approval in approvals),
            "invalidated": sum(approval.status == "invalidated" for approval in approvals),
        }

    def briefs_latest(self, project_id: str | None = None) -> DailyBriefRecord | None:
        if project_id:
            rows = self.database.connection.execute(
                "SELECT * FROM daily_briefs WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            ).fetchone()
        else:
            rows = self.database.connection.execute(
                "SELECT * FROM daily_briefs ORDER BY created_at DESC LIMIT 1",
            ).fetchone()
        return self._brief_from_row(rows) if rows else None

    @staticmethod
    def _ensure_codex_marker(draft_type: DraftType, content: str) -> str:
        if draft_type == "codex_prompt" and "DRAFT - NOT EXECUTED" not in content:
            return "DRAFT - NOT EXECUTED\n\n" + content.lstrip()
        return content
