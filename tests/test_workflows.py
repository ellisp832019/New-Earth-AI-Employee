from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from gaia.agent import AgentService
from gaia.api import create_app
from gaia.cli import app
from gaia.db import Database
from gaia.local_ai_runtime import LocalAIRuntimeClient
from gaia.service import ProjectService
from gaia.workflows import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    DraftCreateRequest,
    DraftReviseRequest,
    TaskCreateRequest,
    TaskTransitionRequest,
    TaskUpdateRequest,
    TaskWorkflowService,
    ValidationError,
)


def _workflow_service(settings) -> TaskWorkflowService:
    return TaskWorkflowService(settings, Database(settings.database_path))


def _create_agent_run(settings) -> str:
    database = Database(settings.database_path)
    service = ProjectService(settings, database)
    runtime_client = LocalAIRuntimeClient(settings.local_ai_runtime)
    agent = AgentService(service, database, runtime_client)
    try:
        response = asyncio.run(
            agent.ask(
                "sample",
                "What was completed most recently?",
                deterministic_only=True,
            )
        )
        return response.run_id
    finally:
        database.close()


def test_database_migration_preserves_existing_data(tmp_path: Path):
    old_db = tmp_path / "legacy.db"
    connection = sqlite3.connect(old_db)
    connection.execute(
        "CREATE TABLE documents (project_id TEXT NOT NULL, relative_path TEXT NOT NULL, extension TEXT NOT NULL, size_bytes INTEGER NOT NULL, modified_utc TEXT NOT NULL, sha256 TEXT NOT NULL, tracked INTEGER, indexing_status TEXT NOT NULL, warning TEXT, scanned_at TEXT NOT NULL, content TEXT, PRIMARY KEY(project_id, relative_path))"
    )
    connection.execute(
        "INSERT INTO documents(project_id, relative_path, extension, size_bytes, modified_utc, sha256, tracked, indexing_status, warning, scanned_at, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("sample", "README.md", ".md", 10, "2026-08-05T00:00:00+00:00", "abc", 1, "indexed", None, "2026-08-05T00:00:00+00:00", "hello"),
    )
    connection.execute("PRAGMA user_version = 3")
    connection.commit()
    connection.close()

    migrated = Database(old_db)
    try:
        assert migrated.connection.execute("PRAGMA user_version").fetchone()[0] == 13
        row = migrated.connection.execute("SELECT relative_path FROM documents").fetchone()
        assert row[0] == "README.md"
        migrated.connection.execute("SELECT count(*) FROM tasks").fetchone()
    finally:
        migrated.close()


def test_task_lifecycle_and_invalid_transition(settings):
    workflow = _workflow_service(settings)
    try:
        task = workflow.create_task(
            TaskCreateRequest(
                title="Write controlled workflow docs",
                project_id="sample",
                description="Document the task centre",
                source_type="manual",
                completion_criteria="Docs committed",
            )
        )
        assert task.status == "proposed"
        task = workflow.accept_task(task.task_id)
        assert task.status == "backlog"
        task = workflow.transition_task(task.task_id, TaskTransitionRequest(version=task.version, status="ready"))
        assert task.status == "ready"
        task = workflow.transition_task(task.task_id, TaskTransitionRequest(version=task.version, status="in_progress"))
        assert task.status == "in_progress"
        task = workflow.transition_task(
            task.task_id,
            TaskTransitionRequest(version=task.version, status="awaiting_approval", reason="ready for review"),
        )
        assert task.status == "awaiting_approval"
        task = workflow.transition_task(
            task.task_id,
            TaskTransitionRequest(
                version=task.version,
                status="completed",
                completion_evidence=["docs/USER_GUIDE.md"],
                reason="approved",
            ),
        )
        assert task.status == "completed"
        with pytest.raises(ValidationError):
            workflow.transition_task(task.task_id, TaskTransitionRequest(version=task.version, status="backlog"))
        history = workflow.task_history(task.task_id)
        assert history[0].to_status == "proposed"
        assert history[-1].to_status == "completed"
    finally:
        workflow.close()


def test_task_from_agent_run_and_history(settings):
    run_id = _create_agent_run(settings)
    workflow = _workflow_service(settings)
    try:
        task = workflow.create_task_from_run(run_id)
        assert task.status == "proposed"
        assert task.source_agent_run_id == run_id
        assert workflow.task_history(task.task_id)[0].action == "create"
        with pytest.raises(ValidationError):
            workflow.create_task(
                TaskCreateRequest(
                    title="Active agent task",
                    project_id="sample",
                    source_type="agent_run",
                    source_agent_run_id=run_id,
                    status="ready",
                )
            )
    finally:
        workflow.close()


def test_draft_revision_and_approval_invalidation(settings):
    workflow = _workflow_service(settings)
    try:
        task = workflow.create_task(
            TaskCreateRequest(
                title="Draft the next Codex prompt",
                project_id="sample",
                source_type="manual",
                approval_requirement=True,
            )
        )
        draft, revision = workflow.create_draft(
            DraftCreateRequest(
                title="Next Codex prompt",
                draft_type="codex_prompt",
                project_id="sample",
                source_task_id=task.task_id,
                content="Ask for the next implementation step.",
                approval_requirement=True,
            )
        )
        assert "DRAFT - NOT EXECUTED" in revision.content
        approval = workflow.create_approval(
            ApprovalCreateRequest(
                title="Manual use approval",
                project_id="sample",
                source_task_id=task.task_id,
                source_draft_id=draft.draft_id,
                requesting_source="manual",
                proposed_action="Use the prompt in the next session",
                exact_target_description="GAIA prompt review",
                preview_summary="Prompt ready for manual use",
                approved_content_hash=draft.current_content_hash,
            )
        )
        approved = workflow.approve(approval.approval_id, ApprovalDecisionRequest(version=approval.version, reviewer="Peter", decision_reason="Approved for manual use"))
        assert approved.status == "approved_for_manual_use"
        workflow.revise_draft(
            draft.draft_id,
            DraftReviseRequest(version=draft.current_revision, content="Revise the prompt with the new workflow scope."),
        )
        refreshed = workflow.refresh_approval_validation(approval.approval_id)
        assert refreshed.status == "invalidated"
        with pytest.raises(ValidationError):
            workflow.create_approval(
                ApprovalCreateRequest(
                    title="Prohibited approval",
                    project_id="sample",
                    risk_level="prohibited",
                )
            )
    finally:
        workflow.close()


def test_completed_task_cannot_lose_completion_evidence(settings):
    workflow = _workflow_service(settings)
    try:
        task = workflow.create_task(
            TaskCreateRequest(
                title="Complete with evidence",
                project_id="sample",
                source_type="manual",
                completion_criteria="evidence required",
            )
        )
        task = workflow.accept_task(task.task_id)
        task = workflow.transition_task(task.task_id, TaskTransitionRequest(version=task.version, status="ready"))
        task = workflow.transition_task(task.task_id, TaskTransitionRequest(version=task.version, status="in_progress"))
        task = workflow.transition_task(
            task.task_id,
            TaskTransitionRequest(version=task.version, status="awaiting_approval", reason="ready for review"),
        )
        task = workflow.transition_task(
            task.task_id,
            TaskTransitionRequest(
                version=task.version,
                status="completed",
                completion_evidence=["docs/USER_GUIDE.md"],
                reason="done",
            ),
        )
        with pytest.raises(ValidationError):
            workflow.update_task(
                task.task_id,
                TaskUpdateRequest(version=task.version, completion_evidence=[]),
            )
    finally:
        workflow.close()


def test_approval_rejection_reason_and_self_approval_rules(settings):
    workflow = _workflow_service(settings)
    try:
        manual = workflow.create_approval(
            ApprovalCreateRequest(
                title="Manual approval",
                project_id="sample",
                requesting_source="manual",
                proposed_action="Review locally",
            )
        )
        approved = workflow.approve(
            manual.approval_id,
            ApprovalDecisionRequest(version=manual.version, reviewer="manual", decision_reason="Approved for manual use"),
        )
        assert approved.status == "approved_for_manual_use"

        model = workflow.create_approval(
            ApprovalCreateRequest(
                title="Model approval",
                project_id="sample",
                requesting_source="model",
                proposed_action="Review locally",
            )
        )
        with pytest.raises(ValidationError):
            workflow.approve(
                model.approval_id,
                ApprovalDecisionRequest(version=model.version, reviewer="model", decision_reason="Approved for manual use"),
            )
        with pytest.raises(ValidationError):
            workflow.reject_approval(
                model.approval_id,
                ApprovalDecisionRequest(version=model.version, reviewer="manual", decision_reason=""),
            )
    finally:
        workflow.close()


def test_daily_brief_generation(settings):
    workflow = _workflow_service(settings)
    try:
        workflow.project_service.scan("sample")
        task = workflow.create_task(TaskCreateRequest(title="Review backlog", project_id="sample"))
        brief = workflow.daily_brief("sample")
        assert "Daily Operations Brief" in brief.markdown
        assert brief.verified_facts
        assert task.task_id in brief.source_task_ids
    finally:
        workflow.close()


def test_api_workflow_endpoints(settings):
    with TestClient(create_app(settings)) as client:
        task = client.post("/tasks", json={"title": "API task", "project_id": "sample"})
        assert task.status_code == 200
        task_id = task.json()["task_id"]
        assert client.get(f"/tasks/{task_id}").status_code == 200
        assert client.post(f"/tasks/{task_id}/accept").status_code == 200
        draft = client.post(
            "/drafts",
            json={
                "title": "API draft",
                "draft_type": "codex_prompt",
                "project_id": "sample",
                "content": "Build the next workflow step.",
                "approval_requirement": True,
            },
        )
        assert draft.status_code == 200
        draft_id = draft.json()["draft_id"]
        approval = client.post(
            "/approvals",
            json={
                "title": "API approval",
                "project_id": "sample",
                "source_draft_id": draft_id,
                "requesting_source": "manual",
                "proposed_action": "Use prompt manually",
                "exact_target_description": "Manual review",
                "preview_summary": "Safe summary",
                "approved_content_hash": draft.json()["current_content_hash"],
            },
        )
        assert approval.status_code == 200
        brief = client.post("/briefs/daily", params={"project_id": "sample"})
        assert brief.status_code == 200
        assert client.get("/integration/v1/status").status_code == 200
        assert client.get("/integration/v1/tasks/summary").status_code == 200
        assert client.get("/integration/v1/approvals/summary").status_code == 200
        assert client.get("/integration/v1/briefs/latest").status_code == 200


def test_cli_workflow_commands(settings_file: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["tasks", "create", "CLI task", "--project-id", "sample", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "CLI task" in result.output
    result = runner.invoke(app, ["briefs", "daily", "--project-id", "sample", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "Daily Operations Brief" in result.output
