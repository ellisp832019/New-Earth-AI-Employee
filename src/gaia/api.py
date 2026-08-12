from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from gaia import __version__
from gaia.agent import AgentService
from gaia.change_impact import ChangeImpactChangeType, ChangeProposal, ChangeProposalTarget
from gaia.config import Settings, load_settings
from gaia.conversation import AskRequest
from gaia.db import Database
from gaia.local_ai_runtime import LocalAIRuntimeClient
from gaia.models import HealthResponse, ProjectRecommendation
from gaia.output_workspace import (
    OutputActionCreateRequest,
    OutputWorkspaceError,
    OutputWorkspaceService,
    PathSafetyError,
    PermissionManifestCreateRequest,
    PermissionManifestDecisionRequest,
)
from gaia.output_workspace import PermissionDeniedError as OutputPermissionDeniedError
from gaia.project_officer import (
    ProjectOfficerApiError,
    ProjectOfficerAuthorityLevel,
    ProjectOfficerHandoffRequest,
    ProjectOfficerLifecycleRequest,
    ProjectOfficerOutcomeRequest,
    ProjectOfficerService,
)
from gaia.provenance import ProvenanceCreateRequest
from gaia.providers import ProviderRegistry
from gaia.service import ProjectService
from gaia.trust import GAIATrustService
from gaia.workflows import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ConflictError,
    DraftCreateRequest,
    DraftReviseRequest,
    NotFoundError,
    TaskCreateRequest,
    TaskTransitionRequest,
    TaskUpdateRequest,
    TaskWorkflowService,
    ValidationError,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    database = Database(resolved_settings.database_path)
    service = ProjectService(resolved_settings, database)
    runtime_client = LocalAIRuntimeClient(resolved_settings.local_ai_runtime)
    provider_registry = ProviderRegistry(resolved_settings.local_ai_runtime, runtime_client)
    agent_service = AgentService(service, database, runtime_client)
    workflow_service = TaskWorkflowService(resolved_settings, database)
    output_service = OutputWorkspaceService(resolved_settings, database)
    trust_service = GAIATrustService(resolved_settings, database)
    project_officer_service = ProjectOfficerService(service)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service.audit.record(category="application", operation="startup", outcome="success")
        trust_service.seed_templates()
        trust_service.seed_retention_policies()
        yield
        service.close()

    app = FastAPI(
        title="GAIA Project-Control API",
        version=__version__,
        description="Read-only local project inspection and evidence reporting.",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.service = service

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=__version__,
            database_path=str(resolved_settings.database_path),
            fts5_available=database.fts5_available,
        )

    @app.get("/governance")
    def governance_context(project_id: str | None = None, finding_id: str | None = None) -> dict[str, object]:
        return service.governance_context(project_id=project_id, finding_id=finding_id).model_dump(mode="json")

    @app.get("/governance/status")
    def governance_status(project_id: str | None = None) -> dict[str, object]:
        return service.governance_status(project_id=project_id).model_dump(mode="json")

    @app.get("/governance/findings")
    def governance_findings(project_id: str | None = None) -> dict[str, object]:
        return service.governance_findings(project_id=project_id).model_dump(mode="json")

    @app.get("/governance/project/{project_id}")
    def governance_project(project_id: str) -> dict[str, object]:
        return service.governance_project(project_id).model_dump(mode="json")

    @app.get("/governance/snapshot")
    def governance_snapshot() -> dict[str, object]:
        return service.governance_snapshot().model_dump(mode="json")

    @app.get("/governance/brief")
    def governance_brief(project_id: str | None = None) -> dict[str, object]:
        return service.governance_brief(project_id=project_id).model_dump(mode="json")

    @app.get("/projects")
    def projects() -> list[dict[str, object]]:
        return [project.public_payload() for project in resolved_settings.projects.values()]

    @app.get("/projects/{project_id}")
    def project(project_id: str) -> dict[str, object]:
        try:
            return service.get_project(project_id).public_payload()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.post("/projects/{project_id}/scan")
    def scan(project_id: str) -> dict[str, object]:
        try:
            documents = service.scan(project_id)
            return {"project_id": project_id, "document_count": len(documents), "documents": documents}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=409, detail="Configured project root does not exist") from exc

    @app.get("/projects/{project_id}/snapshots")
    def snapshots(project_id: str) -> list[dict[str, object]]:
        try:
            service.get_project(project_id)
            return [item.model_dump(mode="json") for item in database.list_snapshots(project_id)]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/projects/{project_id}/snapshots/latest")
    def latest_snapshot(project_id: str) -> dict[str, object]:
        try:
            service.get_project(project_id)
            item = database.latest_snapshot(project_id)
            if not item:
                raise HTTPException(status_code=404, detail="No snapshot exists")
            return item.model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/projects/{project_id}/documents")
    def documents(project_id: str) -> list[dict[str, object]]:
        try:
            service.get_project(project_id)
            return database.list_documents(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/projects/{project_id}/search")
    def search(
        project_id: str,
        q: str = Query(min_length=1, max_length=500),
        limit: int = Query(default=20, ge=1, le=100),
        path_prefix: str | None = None,
        extension: str | None = None,
    ) -> list[dict[str, object]]:
        try:
            return [
                result.model_dump(mode="json")
                for result in service.search(project_id, q, limit, path_prefix, extension)
            ]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.post("/projects/{project_id}/reports/foundation", response_class=PlainTextResponse)
    def report(project_id: str, format: str = Query(default="markdown", pattern="^(markdown|json)$")) -> str:
        try:
            return service.foundation_report(project_id, format)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.post("/projects/{project_id}/health")
    def capture_project_health(project_id: str) -> dict[str, object]:
        try:
            return service.project_health(project_id).model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/projects/{project_id}/health")
    def latest_project_health(project_id: str) -> dict[str, object]:
        try:
            snapshot = service.latest_project_health_snapshot(project_id)
            if snapshot is None:
                raise HTTPException(status_code=404, detail="No project health snapshot exists")
            return snapshot.model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/projects/{project_id}/health/snapshots")
    def project_health_snapshots(project_id: str) -> list[dict[str, object]]:
        try:
            service.get_project(project_id)
            return [snapshot.model_dump(mode="json") for snapshot in service.project_health_snapshots(project_id)]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/portfolio/health")
    def health_portfolio() -> dict[str, object]:
        return service.project_health_portfolio().model_dump(mode="json")

    @app.get("/portfolio/changes")
    def change_portfolio() -> dict[str, object]:
        return service.project_change_portfolio().model_dump(mode="json")

    @app.get("/portfolio/recommendations")
    def recommendation_portfolio() -> dict[str, object]:
        return service.project_recommendation_portfolio().model_dump(mode="json")

    @app.get("/projects/{project_id}/changes/findings")
    def project_change_findings(project_id: str) -> list[dict[str, object]]:
        try:
            service.get_project(project_id)
            return [finding.model_dump(mode="json") for finding in service.list_project_change_findings(project_id)]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/projects/{project_id}/recommendations")
    def project_recommendations(project_id: str) -> list[dict[str, object]]:
        try:
            service.get_project(project_id)
            return [item.model_dump(mode="json") for item in service.list_project_recommendations(project_id)]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.post("/projects/{project_id}/recommendations/generate")
    def generate_project_recommendations(project_id: str) -> list[dict[str, object]]:
        try:
            return [item.model_dump(mode="json") for item in service.generate_project_recommendations(project_id)]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/recommendations/queue")
    def recommendation_queue(project_id: str | None = None) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in service.recommendation_queue(project_id)]

    @app.get("/recommendations/{recommendation_id}")
    def recommendation(recommendation_id: str) -> dict[str, object]:
        item = service.get_project_recommendation(recommendation_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return item.model_dump(mode="json")

    @app.post("/recommendations/{recommendation_id}/work-packages")
    def generate_work_package(recommendation_id: str) -> dict[str, object]:
        try:
            return service.generate_work_package(recommendation_id).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/work-packages")
    def work_packages(
        project_id: str | None = None,
        approval_state: str | None = None,
        staleness_state: str | None = None,
    ) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in service.work_packages(
                project_id=project_id,
                approval_state=approval_state,
                staleness_state=staleness_state,
            )
        ]

    @app.get("/work-packages/{work_package_id}")
    def get_work_package(work_package_id: str) -> dict[str, object]:
        item = service.get_work_package(work_package_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Work package not found")
        return item.model_dump(mode="json")

    @app.get("/work-packages/{work_package_id}/revisions")
    def work_package_revisions(work_package_id: str) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in service.work_package_revisions(work_package_id)]

    @app.get("/work-packages/{work_package_id}/approval-decisions")
    def work_package_approval_decisions(work_package_id: str) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in service.work_package_approval_decisions(work_package_id)]

    @app.get("/work-packages/{work_package_id}/handoffs")
    def work_package_handoffs(work_package_id: str) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in service.work_package_handoffs(work_package_id)]

    @app.get("/work-packages/{work_package_id}/outcomes")
    def work_package_outcomes(work_package_id: str) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in service.work_package_outcomes(work_package_id)]

    @app.get("/work-packages/{work_package_id}/summary")
    def work_package_summary(work_package_id: str) -> dict[str, object]:
        try:
            return service.work_package_summary(work_package_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/work-packages/{work_package_id}/prompt")
    def work_package_prompt(work_package_id: str, revision_number: int | None = None) -> dict[str, object]:
        try:
            return {
                "work_package_id": work_package_id,
                "revision_number": revision_number,
                "prompt": service.render_work_package_prompt(work_package_id, revision_number=revision_number),
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/work-packages/{work_package_id}/staleness/detect")
    def detect_work_package_staleness(work_package_id: str) -> dict[str, object]:
        try:
            return service.detect_work_package_staleness(work_package_id).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/work-packages/{work_package_id}/expire")
    def expire_work_package(work_package_id: str, reason: str = Body(default="manual expiry")) -> dict[str, object]:
        try:
            return service.expire_work_package(work_package_id, reason=reason).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/work-packages/{work_package_id}/submit-for-review")
    def submit_work_package_for_review(
        work_package_id: str,
        revision_number: int = Query(..., ge=1),
        actor: str = Query(default="manual"),
    ) -> dict[str, object]:
        try:
            return service.work_package_submit_for_review(work_package_id, revision_number, actor=actor).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/work-packages/{work_package_id}/approve")
    def approve_work_package(
        work_package_id: str,
        revision_number: int = Query(..., ge=1),
        actor: str = Query(default="manual"),
        human_note: str | None = None,
    ) -> dict[str, object]:
        try:
            return service.work_package_approve(
                work_package_id,
                revision_number,
                actor=actor,
                human_note=human_note,
            ).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/work-packages/{work_package_id}/reject")
    def reject_work_package(
        work_package_id: str,
        revision_number: int = Query(..., ge=1),
        actor: str = Query(default="manual"),
        human_note: str | None = None,
    ) -> dict[str, object]:
        try:
            return service.work_package_reject(
                work_package_id,
                revision_number,
                actor=actor,
                human_note=human_note,
            ).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/work-packages/{work_package_id}/handoff")
    def handoff_work_package(
        work_package_id: str,
        revision_number: int = Query(..., ge=1),
        approved_by: str = Query(default="manual"),
        next_manual_action: str = Query(default="Copy the approved Codex prompt into Codex."),
        rollback_reference: str = Query(default="Return to the recorded baseline commit or last approved revision."),
    ) -> dict[str, object]:
        try:
            return service.work_package_handoff(
                work_package_id,
                revision_number,
                approved_by=approved_by,
                next_manual_action=next_manual_action,
                rollback_reference=rollback_reference,
            ).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/work-packages/{work_package_id}/outcome")
    def record_work_package_outcome(
        work_package_id: str,
        revision_number: int = Query(..., ge=1),
        outcome: str = Query(...),
        actor: str = Query(default="manual"),
        note: str | None = None,
    ) -> dict[str, object]:
        try:
            return service.work_package_record_outcome(
                work_package_id,
                revision_number,
                outcome=outcome,
                actor=actor,
                note=note,
            ).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.patch("/work-packages/{work_package_id}/revise")
    def revise_work_package(
        work_package_id: str,
        request: dict[str, object] = Body(default={}),
    ) -> dict[str, object]:
        try:
            raw_field_updates = request.get("field_updates")
            field_updates = cast(dict[str, object], raw_field_updates) if isinstance(raw_field_updates, dict) else None
            return service.revise_work_package(
                work_package_id,
                change_reason=str(request.get("change_reason", "revision")),
                field_updates=field_updates,
                actor=str(request.get("actor", "manual")),
            ).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/audit/events")
    def audit_events(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict[str, object]]:
        return database.list_audit_events(limit)

    @app.get("/models/status")
    async def models_status() -> list[dict[str, object]]:
        return [status.model_dump(mode="json") for status in await provider_registry.list_status()]

    @app.get("/models")
    async def models() -> dict[str, object]:
        try:
            return (await runtime_client.models()).model_dump(mode="json")
        except Exception as exc:
            return {
                "service": "new-earth-local-ai-runtime",
                "version": __version__,
                "models": [],
                "degraded": True,
                "details": str(exc),
            }

    @app.post("/agent/ask")
    async def ask(request: AskRequest) -> dict[str, object]:
        try:
            response = await agent_service.ask(
                request.project_id,
                request.question,
                provider=request.provider,
                model=request.model,
                evidence_limit=request.evidence_limit,
                refresh_snapshot=request.refresh_snapshot,
                deterministic_only=request.deterministic_only,
            )
            return response.model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def _workflow_http_error(error: Exception) -> HTTPException:
        if isinstance(error, NotFoundError):
            return HTTPException(status_code=404, detail=str(error))
        if isinstance(error, ConflictError):
            return HTTPException(status_code=409, detail=str(error))
        if isinstance(error, ValidationError):
            return HTTPException(status_code=400, detail=str(error))
        return HTTPException(status_code=500, detail=str(error))

    def _output_http_error(error: Exception) -> HTTPException:
        if isinstance(error, PathSafetyError):
            return HTTPException(status_code=400, detail=str(error))
        if isinstance(error, OutputPermissionDeniedError):
            return HTTPException(status_code=403, detail=str(error))
        if isinstance(error, OutputWorkspaceError):
            return HTTPException(status_code=400, detail=str(error))
        if isinstance(error, ConflictError):
            return HTTPException(status_code=409, detail=str(error))
        return HTTPException(status_code=500, detail=str(error))

    def _project_officer_http_error(
        error: Exception,
        *,
        resource_type: str,
        resource_id: str | None = None,
        authority_level: ProjectOfficerAuthorityLevel | None = None,
        details: dict[str, object] | None = None,
    ) -> HTTPException:
        message = str(error)
        error_code = f"backend_{type(error).__name__.lower()}"
        status_code = 400
        if isinstance(error, KeyError):
            status_code = 404
            error_code = {
                "project": "unknown_project",
                "project_health_snapshot": "unknown_snapshot",
                "change_finding": "unknown_finding",
                "recommendation": "unknown_recommendation",
                "work_package": "unknown_work_package",
                "work_package_revision": "unknown_revision",
            }.get(resource_type, "not_found")
        elif isinstance(error, PermissionError):
            status_code = 409
            error_code = "blocked_action"
        elif isinstance(error, ValueError):
            status_code = 409
            lowered = message.lower()
            if "stale or expired work packages cannot transition" in lowered:
                error_code = "stale_package"
            elif "blocked work packages cannot be approved or handed off" in lowered:
                error_code = "blocked_action"
            elif "prior approval decision is required before handoff" in lowered:
                error_code = "blocked_action"
            elif "cross-project" in lowered:
                error_code = "project_revision_mismatch"
            else:
                error_code = "invalid_state_transition"
        error_payload = ProjectOfficerApiError(
            error_code=error_code,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            authority_level=authority_level,
            details=details or {},
        )
        return HTTPException(status_code=status_code, detail=error_payload.model_dump(mode="json"))

    @app.get("/agent/runs")
    def agent_runs(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict[str, object]]:
        return database.list_agent_runs(limit)

    @app.get("/agent/runs/{run_id}")
    def agent_run(run_id: str) -> dict[str, object]:
        run = database.get_agent_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @app.get("/tasks")
    def tasks(
        project_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        return [
            task.model_dump(mode="json")
            for task in workflow_service.list_tasks(project_id=project_id, status=status, priority=priority, limit=limit, offset=offset)
        ]

    @app.post("/tasks")
    def create_task(request: TaskCreateRequest) -> dict[str, object]:
        try:
            return workflow_service.create_task(request).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, object]:
        try:
            return workflow_service.get_task(task_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.patch("/tasks/{task_id}")
    def update_task(task_id: str, request: TaskUpdateRequest) -> dict[str, object]:
        try:
            return workflow_service.update_task(task_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/tasks/{task_id}/history")
    def task_history(task_id: str) -> list[dict[str, object]]:
        try:
            return [item.model_dump(mode="json") for item in workflow_service.task_history(task_id)]
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/tasks/{task_id}/accept")
    def accept_task(task_id: str) -> dict[str, object]:
        try:
            return workflow_service.accept_task(task_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/tasks/{task_id}/transition")
    def transition_task(task_id: str, request: TaskTransitionRequest) -> dict[str, object]:
        try:
            return workflow_service.transition_task(task_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/tasks/{task_id}/cancel")
    def cancel_task(task_id: str) -> dict[str, object]:
        try:
            return workflow_service.cancel_task(task_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/tasks/from-agent-run/{run_id}")
    def task_from_run(run_id: str) -> dict[str, object]:
        try:
            return workflow_service.create_task_from_run(run_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/drafts")
    def drafts(
        project_id: str | None = None,
        status: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        return [
            draft.model_dump(mode="json")
            for draft in workflow_service.list_drafts(project_id=project_id, status=status, limit=limit, offset=offset)
        ]

    @app.post("/drafts")
    def create_draft(request: DraftCreateRequest) -> dict[str, object]:
        try:
            draft, _revision = workflow_service.create_draft(request)
            return draft.model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/drafts/{draft_id}")
    def get_draft(draft_id: str) -> dict[str, object]:
        try:
            return workflow_service.get_draft(draft_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.patch("/drafts/{draft_id}")
    def revise_draft(draft_id: str, request: DraftReviseRequest) -> dict[str, object]:
        try:
            draft, _revision = workflow_service.revise_draft(draft_id, request)
            return draft.model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/drafts/{draft_id}/revisions")
    def draft_revisions(draft_id: str) -> list[dict[str, object]]:
        try:
            return [revision.model_dump(mode="json") for revision in workflow_service.draft_revisions(draft_id)]
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/drafts/{draft_id}/revise")
    def draft_revise(draft_id: str, request: DraftReviseRequest) -> dict[str, object]:
        try:
            draft, _revision = workflow_service.revise_draft(draft_id, request)
            return draft.model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/drafts/{draft_id}/submit-for-review")
    def submit_draft(draft_id: str) -> dict[str, object]:
        try:
            return workflow_service.submit_draft_for_review(draft_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/drafts/{draft_id}/reject")
    def reject_draft(draft_id: str) -> dict[str, object]:
        try:
            return workflow_service.reject_draft(draft_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/drafts/{draft_id}/supersede")
    def supersede_draft(draft_id: str) -> dict[str, object]:
        try:
            return workflow_service.supersede_draft(draft_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/approvals")
    def approvals(
        project_id: str | None = None,
        status: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        return [
            approval.model_dump(mode="json")
            for approval in workflow_service.list_approvals(project_id=project_id, status=status, limit=limit, offset=offset)
        ]

    @app.post("/approvals")
    def create_approval(request: ApprovalCreateRequest) -> dict[str, object]:
        try:
            return workflow_service.create_approval(request).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/approvals/{approval_id}")
    def get_approval(approval_id: str) -> dict[str, object]:
        try:
            return workflow_service.get_approval(approval_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/approvals/{approval_id}/approve")
    def approve_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, object]:
        try:
            return workflow_service.approve(approval_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/approvals/{approval_id}/reject")
    def reject_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, object]:
        try:
            return workflow_service.reject_approval(approval_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/approvals/{approval_id}/cancel")
    def cancel_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, object]:
        try:
            return workflow_service.cancel_approval(approval_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/approvals/{approval_id}/refresh-validation")
    def refresh_approval_validation(approval_id: str) -> dict[str, object]:
        try:
            return workflow_service.refresh_approval_validation(approval_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.post("/briefs/daily")
    def daily_brief(project_id: str) -> dict[str, object]:
        try:
            return workflow_service.daily_brief(project_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/briefs")
    def briefs(project_id: str | None = None, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> list[dict[str, object]]:
        return [brief.model_dump(mode="json") for brief in workflow_service.list_briefs(project_id=project_id, limit=limit, offset=offset)]

    @app.get("/briefs/{brief_id}")
    def get_brief(brief_id: str) -> dict[str, object]:
        try:
            return workflow_service.get_brief(brief_id).model_dump(mode="json")
        except Exception as exc:
            raise _workflow_http_error(exc) from exc

    @app.get("/permissions")
    def permissions() -> list[dict[str, object]]:
        return [manifest.model_dump(mode="json") for manifest in output_service.list_permission_manifests()]

    @app.post("/permissions")
    def create_permission_manifest(request: PermissionManifestCreateRequest) -> dict[str, object]:
        try:
            return output_service.create_permission_manifest(request).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.get("/permissions/{manifest_id}")
    def get_permission_manifest(manifest_id: str) -> dict[str, object]:
        try:
            return output_service.get_permission_manifest(manifest_id).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/permissions/{manifest_id}/validate")
    def validate_permission_manifest(manifest_id: str) -> dict[str, object]:
        try:
            return output_service.validate_permission_manifest(manifest_id)
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/permissions/{manifest_id}/review")
    def review_permission_manifest(manifest_id: str, request: PermissionManifestDecisionRequest) -> dict[str, object]:
        try:
            return output_service.update_permission_manifest(manifest_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.get("/actions")
    def actions(project_id: str | None = None, status: str | None = None, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> list[dict[str, object]]:
        return [
            action.model_dump(mode="json")
            for action in output_service.list_actions(project_id=project_id, status=status, limit=limit, offset=offset)
        ]

    @app.post("/actions")
    def create_action(request: OutputActionCreateRequest) -> dict[str, object]:
        try:
            return output_service.create_action(request).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.get("/actions/{action_id}")
    def get_action(action_id: str) -> dict[str, object]:
        try:
            return output_service.get_action(action_id).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/actions/{action_id}/preview")
    def preview_action(action_id: str) -> dict[str, object]:
        try:
            action = output_service.get_action(action_id)
            previews = output_service.action_previews(action_id)
            return {
                "action": action.model_dump(mode="json"),
                "previews": [preview.model_dump(mode="json") for preview in previews],
            }
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/actions/{action_id}/request-approval")
    def request_action_approval(action_id: str) -> dict[str, object]:
        try:
            approval = output_service.request_approval(action_id)
            return approval.model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/actions/{action_id}/approve")
    def approve_action(action_id: str) -> dict[str, object]:
        try:
            return output_service.approve_action(action_id).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/actions/{action_id}/execute")
    def execute_action(action_id: str, confirm: bool = Query(default=False), operator: str = Query(default="manual")) -> dict[str, object]:
        try:
            if not confirm:
                raise OutputWorkspaceError("Execution confirmation is required.")
            action, receipt = output_service.execute_action(action_id, confirmation_token=action_id, operator=operator)
            return {"action": action.model_dump(mode="json"), "receipt": receipt.model_dump(mode="json")}
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/actions/{action_id}/rollback")
    def rollback_action(action_id: str, confirm: bool = Query(default=False), operator: str = Query(default="manual")) -> dict[str, object]:
        try:
            if not confirm:
                raise OutputWorkspaceError("Rollback confirmation is required.")
            action, rollback = output_service.rollback_action(action_id, confirmation_token=action_id, operator=operator)
            return {"action": action.model_dump(mode="json"), "rollback": rollback.model_dump(mode="json")}
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/actions/{action_id}/cancel")
    def cancel_action(action_id: str, reason: str = Query(default="cancelled")) -> dict[str, object]:
        try:
            return output_service.cancel_action(action_id, reason).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.get("/receipts")
    def receipts(limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> list[dict[str, object]]:
        return [receipt.model_dump(mode="json") for receipt in output_service.list_receipts(limit=limit, offset=offset)]

    @app.get("/receipts/{receipt_id}")
    def receipt(receipt_id: str) -> dict[str, object]:
        try:
            return output_service.get_receipt(receipt_id).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.get("/receipts/{receipt_id}/verify")
    def receipt_verify(receipt_id: str) -> dict[str, object]:
        try:
            return trust_service.verify_receipt(receipt_id).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/receipts/verify-chain")
    def receipt_verify_chain(chain_id: str = Body(embed=True)) -> dict[str, object]:
        return trust_service.verify_chain(chain_id)

    @app.get("/receipts/chains")
    def receipt_chains() -> list[dict[str, object]]:
        return trust_service.list_receipt_chains()

    @app.get("/receipts/chains/{chain_id}")
    def receipt_chain(chain_id: str) -> dict[str, object]:
        try:
            return trust_service.get_receipt_chain(chain_id)
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.get("/receipts/chains/{chain_id}/inspect")
    def receipt_chain_inspect(chain_id: str) -> dict[str, object]:
        try:
            return trust_service.inspect_receipt_chain(chain_id)
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.get("/action-templates")
    def action_templates() -> list[dict[str, object]]:
        return [template.model_dump(mode="json") for template in trust_service.list_action_templates()]

    @app.get("/action-templates/{template_id}")
    def action_template(template_id: str) -> dict[str, object]:
        try:
            return trust_service.get_action_template(template_id).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/action-templates/{template_id}/propose")
    def action_template_propose(template_id: str, request: OutputActionCreateRequest) -> dict[str, object]:
        try:
            return trust_service.template_propose(template_id, request)
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/action-templates/{template_id}/preview")
    def action_template_preview(template_id: str, request: OutputActionCreateRequest) -> dict[str, object]:
        try:
            return trust_service.template_preview(template_id, request)
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.get("/retention/policies")
    def retention_policies() -> list[dict[str, object]]:
        return [policy.model_dump(mode="json") for policy in trust_service.list_retention_policies()]

    @app.get("/retention/status")
    def retention_status() -> dict[str, object]:
        return trust_service.retention_status()

    @app.get("/retention/report")
    def retention_report() -> dict[str, object]:
        return trust_service.retention_report()

    @app.post("/retention/plan")
    def retention_plan(policy_id: str = Body(embed=True)) -> dict[str, object]:
        try:
            return trust_service.plan_retention(policy_id).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/retention/apply")
    def retention_apply(
        plan_id: str = Body(embed=True),
        approved_hash: str = Body(embed=True),
        confirm: bool = Body(default=False, embed=True),
    ) -> dict[str, object]:
        try:
            return trust_service.apply_retention(plan_id, approved_hash, confirm=confirm).model_dump(mode="json")
        except Exception as exc:
            raise _output_http_error(exc) from exc

    @app.post("/review-packages/verify")
    def review_package_verify(package_path: str = Body(embed=True)) -> dict[str, object]:
        return trust_service.verify_review_package(package_path)

    @app.post("/review-packages/inspect")
    def review_package_inspect(package_path: str = Body(embed=True)) -> dict[str, object]:
        return trust_service.inspect_review_package(package_path)

    @app.get("/integration/v1/capabilities")
    def integration_capabilities() -> dict[str, object]:
        return trust_service.provenance.capability_payload()

    @app.get("/integration/v1/project-officer/capabilities")
    def project_officer_capabilities() -> dict[str, object]:
        return project_officer_service.capabilities().model_dump(mode="json")

    @app.get("/integration/v1/project-officer/portfolio")
    def project_officer_portfolio() -> dict[str, object]:
        return project_officer_service.portfolio().model_dump(mode="json")

    @app.get("/integration/v1/project-officer/projects")
    def project_officer_projects() -> list[dict[str, object]]:
        return [project.model_dump(mode="json") for project in project_officer_service.projects()]

    @app.get("/integration/v1/project-officer/projects/{project_id}/health")
    def project_officer_project_health(project_id: str) -> dict[str, object]:
        try:
            return project_officer_service.project_health(project_id).model_dump(mode="json")
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="project", resource_id=project_id, authority_level="read_only") from exc

    @app.get("/integration/v1/project-officer/projects/{project_id}/health/snapshots")
    def project_officer_project_health_snapshots(
        project_id: str,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        try:
            return [
                item.model_dump(mode="json")
                for item in project_officer_service.project_health_snapshots(project_id)[offset : offset + limit]
            ]
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="project", resource_id=project_id, authority_level="read_only") from exc

    @app.get("/integration/v1/project-officer/health-snapshots/{snapshot_id}")
    def project_officer_health_snapshot(snapshot_id: str) -> dict[str, object]:
        snapshot = project_officer_service.project_health_snapshot(snapshot_id)
        if snapshot is None:
            raise _project_officer_http_error(KeyError(snapshot_id), resource_type="project_health_snapshot", resource_id=snapshot_id, authority_level="read_only")
        return snapshot.model_dump(mode="json")

    @app.get("/integration/v1/project-officer/changes/portfolio")
    def project_officer_change_portfolio() -> dict[str, object]:
        return project_officer_service.change_portfolio().model_dump(mode="json")

    def _recommendation_change_type(recommendation_type: str) -> ChangeImpactChangeType:
        return cast(
            ChangeImpactChangeType,
            {
            "review_blocking_project_health_condition": "PROJECT_CONTRACT_CHANGE",
            "review_uncommitted_project_changes": "REPOSITORY_RESTRUCTURE",
            "verify_removal_of_configured_important_project_path": "REPOSITORY_RESTRUCTURE",
            "refresh_project_evidence_before_relying_on_state": "PROJECT_CONTRACT_CHANGE",
            "review_upstream_branch_divergence": "REPOSITORY_RESTRUCTURE",
            "review_repository_head_change": "REPOSITORY_RESTRUCTURE",
            "review_project_configuration_change": "PROJECT_CONTRACT_CHANGE",
            "insufficient_evidence": "PROJECT_CONTRACT_CHANGE",
            }.get(recommendation_type, "PROJECT_CONTRACT_CHANGE"),
        )

    def _proposal_from_recommendation(recommendation: ProjectRecommendation) -> ChangeProposal:
        recommendation_dict = recommendation.model_dump(mode="json")
        project_id = str(recommendation_dict["project_id"])
        title = str(recommendation_dict.get("title") or f"{project_id} change impact review")
        objective = str(
            recommendation_dict.get("concise_summary")
            or recommendation_dict.get("why_it_matters")
            or recommendation_dict.get("rationale")
            or title
        )
        blockers = recommendation_dict.get("blockers") or []
        dependencies = recommendation_dict.get("dependencies") or []
        evidence = recommendation_dict.get("evidence_references") or []
        return ChangeProposal(
            proposal_id=str(recommendation_dict["recommendation_id"]),
            revision=1,
            title=title,
            origin_project=project_id,
            objective=objective,
            change_type=_recommendation_change_type(str(recommendation_dict.get("recommendation_type") or "")),
            target_entities=[
                ChangeProposalTarget(
                    target_kind="project",
                    target_id=project_id,
                    label=str(recommendation_dict.get("project_name") or project_id),
                )
            ],
            evidence=evidence,
            blocked_by=[
                str(item.get("blocker_description") or item.get("required_condition") or item)
                for item in blockers
                if item is not None
            ],
            depends_on=[str(item) for item in dependencies],
            required_validation=[str(item) for item in recommendation_dict.get("source_snapshot_ids") or []],
            rollback_concept=str(recommendation_dict.get("why_it_received_this_score") or title),
            status="analysed",
        )

    def _programme_workspace_payload(project_id: str | None = None) -> dict[str, object]:
        health_portfolio = service.project_health_portfolio()
        change_portfolio = service.project_change_portfolio()
        recommendation_portfolio = service.project_recommendation_portfolio()
        roadmap_portfolio = service.programme_roadmap()
        release_portfolio = service.release_trains()
        package_portfolio = service.programme_packages()
        graph = service.dependency_graph_service.build_graph()
        cycles = service.dependency_graph_service.cycles()
        unresolved = service.dependency_graph_service.unresolved_dependencies()
        shared_dependencies = service.dependency_graph_service.shared_dependencies()
        orphans = service.dependency_graph_service.orphans()
        entities = service.architecture_registry_service.list_entities()
        relationships = service.architecture_registry_service.list_relationships()
        selected_project_id = project_id or (next(iter(sorted(resolved_settings.projects))) if resolved_settings.projects else None)
        selected_project = resolved_settings.projects.get(selected_project_id) if selected_project_id else None
        selected_health = project_officer_service.project_health(selected_project_id) if selected_project_id else None
        selected_health_snapshots = project_officer_service.project_health_snapshots(selected_project_id) if selected_project_id else []
        selected_change_findings = project_officer_service.change_findings(selected_project_id) if selected_project_id else []
        selected_recommendations = project_officer_service.recommendations(project_id=selected_project_id, limit=10) if selected_project_id else []
        selected_work_packages = project_officer_service.work_packages(project_id=selected_project_id, limit=20) if selected_project_id else []
        selected_contract = service.project_contract_service.current_approved_contract(selected_project_id) if selected_project_id else None
        project_dependencies = service.dependency_graph_service.project_dependencies(selected_project_id) if selected_project_id else []
        project_dependents = service.dependency_graph_service.project_dependents(selected_project_id) if selected_project_id else []
        analyses = [
            service.analyse_change_impact(_proposal_from_recommendation(recommendation))
            for recommendation in selected_recommendations[:5]
        ]
        trust_alerts = trust_service.list_trust_alerts()
        provenance_manifests = trust_service.list_provenance_manifests()
        selected_package = package_portfolio.programme_packages[0] if package_portfolio.programme_packages else None
        summary = {
            "project_count": len(resolved_settings.projects),
            "health_status_counts": dict(health_portfolio.counts_by_status),
            "change_severity_counts": dict(change_portfolio.counts_by_severity),
            "recommendation_state_counts": dict(recommendation_portfolio.counts_by_state),
            "roadmap_state_counts": dict(roadmap_portfolio.counts_by_state),
            "release_train_readiness_counts": dict(release_portfolio.counts_by_readiness),
            "package_state_counts": dict(package_portfolio.counts_by_state),
            "architecture_entity_count": len(entities),
            "architecture_relationship_count": len(relationships),
            "cycle_count": len(cycles),
            "unresolved_dependency_count": len(unresolved),
            "shared_dependency_count": len(shared_dependencies),
            "orphan_count": len(orphans),
            "trust_alert_count": len(trust_alerts),
            "provenance_manifest_count": len(provenance_manifests),
            "stale_evidence_projects": list(health_portfolio.projects_without_snapshots),
        }
        return {
            "generated_at": roadmap_portfolio.generated_at.isoformat(),
            "selected_project_id": selected_project_id,
            "selected_project": selected_project.model_dump(mode="json") if selected_project is not None else None,
            "summary": summary,
            "overview": {
                "health_portfolio": health_portfolio.model_dump(mode="json"),
                "change_portfolio": change_portfolio.model_dump(mode="json"),
                "recommendation_portfolio": recommendation_portfolio.model_dump(mode="json"),
                "roadmap_portfolio": roadmap_portfolio.model_dump(mode="json"),
                "release_portfolio": release_portfolio.model_dump(mode="json"),
                "package_portfolio": package_portfolio.model_dump(mode="json"),
            },
            "architecture_registry": {
                "entities": [entity.model_dump(mode="json") for entity in entities],
                "relationships": [relationship.model_dump(mode="json") for relationship in relationships],
                "selected_entity_revisions": [
                    revision.model_dump(mode="json")
                    for revision in service.architecture_registry_service.list_entity_revisions(entities[0].entity_id)
                ]
                if entities
                else [],
                "selected_relationship_revisions": [
                    revision.model_dump(mode="json")
                    for revision in service.architecture_registry_service.list_relationship_revisions(relationships[0].relationship_id)
                ]
                if relationships
                else [],
            },
            "dependency_graph": {
                "snapshot": graph.model_dump(mode="json"),
                "cycles": [cycle.model_dump(mode="json") for cycle in cycles],
                "shared_dependencies": [item.model_dump(mode="json") for item in shared_dependencies],
                "orphans": [item.model_dump(mode="json") for item in orphans],
                "unresolved_findings": [item.model_dump(mode="json") for item in unresolved],
                "project_dependencies": [item.model_dump(mode="json") for item in project_dependencies],
                "project_dependents": [item.model_dump(mode="json") for item in project_dependents],
            },
            "impact_analysis": {
                "analyses": [analysis.model_dump(mode="json") for analysis in analyses],
                "selected_analysis": analyses[0].model_dump(mode="json") if analyses else None,
                "selected_change_findings": [item.model_dump(mode="json") for item in selected_change_findings],
            },
            "change_proposals": {
                "recommendations": [item.model_dump(mode="json") for item in selected_recommendations],
                "selected_recommendation": selected_recommendations[0].model_dump(mode="json") if selected_recommendations else None,
            },
            "roadmap": roadmap_portfolio.model_dump(mode="json"),
            "release_trains": release_portfolio.model_dump(mode="json"),
            "programme_packages": package_portfolio.model_dump(mode="json"),
            "decisions": {
                "selected_work_packages": [item.model_dump(mode="json") for item in selected_work_packages],
                "selected_health_snapshots": [item.model_dump(mode="json") for item in selected_health_snapshots],
                "selected_contract": selected_contract.model_dump(mode="json") if selected_contract is not None else None,
                "trust_alerts": trust_alerts,
            },
            "cross_project_evidence": {
                "provenance_manifests": provenance_manifests,
                "capabilities": trust_service.provenance.capability_payload(),
                "contract_count": len(
                    [item for item in resolved_settings.projects if service.project_contract_service.current_approved_contract(item) is not None]
                ),
                "selected_project_health": selected_health.model_dump(mode="json") if selected_health is not None else None,
                "selected_project_change_findings": [item.model_dump(mode="json") for item in selected_change_findings],
                "selected_project_recommendations": [item.model_dump(mode="json") for item in selected_recommendations],
                "selected_project_work_packages": [item.model_dump(mode="json") for item in selected_work_packages],
                "selected_project_dependencies": [item.model_dump(mode="json") for item in project_dependencies],
                "selected_project_dependents": [item.model_dump(mode="json") for item in project_dependents],
            },
            "selected_package": selected_package.model_dump(mode="json") if selected_package is not None else None,
        }

    def _public_programme_summary_payload(project_id: str | None = None) -> dict[str, object]:
        payload = _programme_workspace_payload(project_id)
        return {
            "generated_at": payload["generated_at"],
            "selected_project_id": payload["selected_project_id"],
            "selected_project": payload["selected_project"],
            "summary": payload["summary"],
            "portfolio": payload["overview"],
            "architecture_registry": payload["architecture_registry"],
            "dependency_graph": payload["dependency_graph"],
            "impact_analysis": payload["impact_analysis"],
            "change_proposals": payload["change_proposals"],
            "roadmap": payload["roadmap"],
            "release_trains": payload["release_trains"],
            "programme_packages": payload["programme_packages"],
            "decisions": payload["decisions"],
            "cross_project_evidence": payload["cross_project_evidence"],
        }

    @app.get("/integration/v1/programme/summary")
    @app.get("/integration/v1/programme/overview")
    def programme_summary(project_id: str | None = None) -> dict[str, object]:
        return _public_programme_summary_payload(project_id)

    @app.get("/integration/v1/architecture/entities")
    def architecture_entities(
        project_id: str | None = None,
        kind: str | None = None,
    ) -> list[dict[str, object]]:
        return [
            entity.model_dump(mode="json")
            for entity in service.architecture_entities(
                project_id=project_id,
                kind=kind,  # type: ignore[arg-type]
            )
        ]

    @app.get("/integration/v1/architecture/entities/{entity_id}")
    def architecture_entity(entity_id: str) -> dict[str, object]:
        entity = service.architecture_entity(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Architecture entity not found")
        return entity.model_dump(mode="json")

    @app.get("/integration/v1/architecture/relationships")
    def architecture_relationships(
        source_entity_id: str | None = None,
        target_entity_id: str | None = None,
        relationship_type: str | None = None,
    ) -> list[dict[str, object]]:
        return [
            relationship.model_dump(mode="json")
            for relationship in service.architecture_relationships(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type,  # type: ignore[arg-type]
            )
        ]

    @app.get("/integration/v1/architecture/relationships/{relationship_id}")
    def architecture_relationship(relationship_id: str) -> dict[str, object]:
        relationship = service.architecture_relationship(relationship_id)
        if relationship is None:
            raise HTTPException(status_code=404, detail="Architecture relationship not found")
        return relationship.model_dump(mode="json")

    @app.get("/integration/v1/dependencies/graph")
    def dependency_graph() -> dict[str, object]:
        return service.dependency_graph().model_dump(mode="json")

    @app.get("/integration/v1/dependencies/findings")
    def dependency_findings() -> list[dict[str, object]]:
        return [finding.model_dump(mode="json") for finding in service.dependency_graph_findings()]

    @app.get("/integration/v1/dependencies/cycles")
    def dependency_cycles() -> list[dict[str, object]]:
        return [cycle.model_dump(mode="json") for cycle in service.dependency_graph_cycles()]

    @app.get("/integration/v1/dependencies/shared")
    def dependency_shared() -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in service.dependency_graph_shared_dependencies()]

    @app.get("/integration/v1/dependencies/orphans")
    def dependency_orphans() -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in service.dependency_graph_orphans()]

    @app.get("/integration/v1/dependencies/projects/{project_id}")
    def dependency_project_dependencies(
        project_id: str,
        transitive: bool = Query(default=False),
    ) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in service.project_dependency_graph(project_id, transitive=transitive)
        ]

    @app.get("/integration/v1/dependencies/projects/{project_id}/dependents")
    def dependency_project_dependents(
        project_id: str,
        transitive: bool = Query(default=False),
    ) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in service.project_dependents_graph(project_id, transitive=transitive)
        ]

    @app.get("/integration/v1/change-impact/summary")
    def change_impact_summary(project_id: str | None = None) -> dict[str, object]:
        recommendation_portfolio = service.project_recommendation_portfolio()
        selected_project_id = project_id or (next(iter(sorted(resolved_settings.projects))) if resolved_settings.projects else None)
        selected_recommendations = [
            recommendation
            for recommendation in service.recommendation_queue(selected_project_id)
            if selected_project_id is None or recommendation.project_id == selected_project_id
        ]
        analyses = [
            service.analyse_change_impact(_proposal_from_recommendation(recommendation))
            for recommendation in selected_recommendations[:5]
        ]
        selected_analysis = analyses[0] if analyses else None
        return {
            "generated_at": recommendation_portfolio.generated_at.isoformat(),
            "selected_project_id": selected_project_id,
            "recommendation_portfolio": recommendation_portfolio.model_dump(mode="json"),
            "change_portfolio": service.project_change_portfolio().model_dump(mode="json"),
            "recommendations": [item.model_dump(mode="json") for item in selected_recommendations],
            "analyses": [analysis.model_dump(mode="json") for analysis in analyses],
            "selected_analysis": selected_analysis.model_dump(mode="json") if selected_analysis is not None else None,
        }

    @app.get("/integration/v1/change-impact/recommendations")
    def change_impact_recommendations(
        project_id: str | None = None,
        priority_tier: str | None = None,
        lifecycle_state: str | None = None,
        blocked_only: bool = False,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        recommendations = project_officer_service.recommendations(
            project_id=project_id,
            priority_tier=priority_tier,
            lifecycle_state=lifecycle_state,
            blocked_only=blocked_only,
            limit=limit,
            offset=offset,
        )
        return [item.model_dump(mode="json") for item in recommendations]

    @app.get("/integration/v1/change-impact/recommendations/{recommendation_id}")
    def change_impact_recommendation(recommendation_id: str) -> dict[str, object]:
        recommendation = project_officer_service.recommendation(recommendation_id)
        if recommendation is None:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return recommendation.model_dump(mode="json")

    @app.get("/integration/v1/programme/roadmap")
    def programme_roadmap() -> dict[str, object]:
        return service.programme_roadmap().model_dump(mode="json")

    @app.get("/integration/v1/release-trains")
    def release_trains() -> dict[str, object]:
        return service.release_trains().model_dump(mode="json")

    @app.get("/integration/v1/programme-packages")
    def programme_packages() -> dict[str, object]:
        return service.programme_packages().model_dump(mode="json")

    @app.get("/integration/v1/programme-packages/{package_id}")
    def programme_package(package_id: str) -> dict[str, object]:
        package = service.programme_package(package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Programme package not found")
        return package.model_dump(mode="json")

    @app.get("/integration/v1/project-officer/projects/{project_id}/changes/findings")
    def project_officer_change_findings(
        project_id: str,
        severity: str | None = Query(default=None),
        direction: str | None = Query(default=None),
        change_type: str | None = Query(default=None),
        status: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        try:
            return [
                item.model_dump(mode="json")
                for item in project_officer_service.change_findings(
                    project_id,
                    severity=severity,
                    direction=direction,
                    change_type=change_type,
                    status=status,
                    limit=limit,
                    offset=offset,
                )
            ]
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="project", resource_id=project_id, authority_level="read_only") from exc

    @app.get("/integration/v1/project-officer/change-findings/{finding_id}")
    def project_officer_change_finding(finding_id: str) -> dict[str, object]:
        finding = project_officer_service.change_finding(finding_id)
        if finding is None:
            raise _project_officer_http_error(KeyError(finding_id), resource_type="change_finding", resource_id=finding_id, authority_level="read_only")
        return finding.model_dump(mode="json")

    @app.get("/integration/v1/project-officer/changes/recent")
    def project_officer_recent_change_findings(
        project_id: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in project_officer_service.recent_change_findings(project_id=project_id, limit=limit)]

    @app.get("/integration/v1/project-officer/programme/workspace", include_in_schema=False)
    def project_officer_programme_workspace(project_id: str | None = None) -> dict[str, object]:
        return _programme_workspace_payload(project_id)

    @app.get("/integration/v1/project-officer/recommendations/portfolio")
    def project_officer_recommendation_portfolio() -> dict[str, object]:
        return project_officer_service.recommendation_portfolio().model_dump(mode="json")

    @app.get("/integration/v1/project-officer/recommendations")
    def project_officer_recommendations(
        project_id: str | None = None,
        priority_tier: str | None = None,
        lifecycle_state: str | None = None,
        blocked_only: bool = False,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in project_officer_service.recommendations(
                project_id=project_id,
                priority_tier=priority_tier,
                lifecycle_state=lifecycle_state,
                blocked_only=blocked_only,
                limit=limit,
                offset=offset,
            )
        ]

    @app.get("/integration/v1/project-officer/recommendations/{recommendation_id}")
    def project_officer_recommendation(recommendation_id: str) -> dict[str, object]:
        recommendation = project_officer_service.recommendation(recommendation_id)
        if recommendation is None:
            raise _project_officer_http_error(KeyError(recommendation_id), resource_type="recommendation", resource_id=recommendation_id, authority_level="read_only")
        return recommendation.model_dump(mode="json")

    @app.get("/integration/v1/project-officer/work-packages")
    def project_officer_work_packages(
        project_id: str | None = None,
        approval_state: str | None = None,
        staleness_state: str | None = None,
        risk_classification: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in project_officer_service.work_packages(
                project_id=project_id,
                approval_state=approval_state,
                staleness_state=staleness_state,
                risk_classification=risk_classification,
                limit=limit,
                offset=offset,
            )
        ]

    @app.get("/integration/v1/project-officer/projects/{project_id}/work-packages")
    def project_officer_project_work_packages(
        project_id: str,
        approval_state: str | None = None,
        staleness_state: str | None = None,
        risk_classification: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in project_officer_service.work_packages(
                project_id=project_id,
                approval_state=approval_state,
                staleness_state=staleness_state,
                risk_classification=risk_classification,
                limit=limit,
                offset=offset,
            )
        ]

    @app.get("/integration/v1/project-officer/work-packages/{work_package_id}")
    def project_officer_work_package(work_package_id: str) -> dict[str, object]:
        package = project_officer_service.work_package(work_package_id)
        if package is None:
            raise _project_officer_http_error(KeyError(work_package_id), resource_type="work_package", resource_id=work_package_id, authority_level="gaia_local_state")
        return package.model_dump(mode="json")

    @app.get("/integration/v1/project-officer/work-packages/{work_package_id}/summary")
    def project_officer_work_package_summary(work_package_id: str) -> dict[str, object]:
        try:
            return project_officer_service.work_package_summary(work_package_id)
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="read_only") from exc

    @app.get("/integration/v1/project-officer/work-packages/{work_package_id}/prompt")
    def project_officer_work_package_prompt(work_package_id: str, revision_number: int | None = None) -> dict[str, object]:
        try:
            return project_officer_service.work_package_prompt(work_package_id, revision_number=revision_number)
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="read_only") from exc

    @app.get("/integration/v1/project-officer/work-packages/{work_package_id}/revisions")
    def project_officer_work_package_revisions(work_package_id: str) -> list[dict[str, object]]:
        try:
            return [item.model_dump(mode="json") for item in project_officer_service.work_package_revisions(work_package_id)]
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="read_only") from exc

    @app.get("/integration/v1/project-officer/work-package-revisions/{revision_id}")
    def project_officer_work_package_revision(revision_id: str) -> dict[str, object]:
        revision = project_officer_service.work_package_revision(revision_id)
        if revision is None:
            raise _project_officer_http_error(KeyError(revision_id), resource_type="work_package_revision", resource_id=revision_id, authority_level="read_only")
        return revision.model_dump(mode="json")

    @app.get("/integration/v1/project-officer/work-packages/{work_package_id}/approval-decisions")
    def project_officer_work_package_approval_decisions(work_package_id: str) -> list[dict[str, object]]:
        try:
            return [item.model_dump(mode="json") for item in project_officer_service.approval_decisions(work_package_id)]
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="read_only") from exc

    @app.get("/integration/v1/project-officer/work-packages/{work_package_id}/handoffs")
    def project_officer_work_package_handoffs(work_package_id: str) -> list[dict[str, object]]:
        try:
            return [item.model_dump(mode="json") for item in project_officer_service.handoffs(work_package_id)]
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="read_only") from exc

    @app.get("/integration/v1/project-officer/work-packages/{work_package_id}/outcomes")
    def project_officer_work_package_outcomes(work_package_id: str) -> list[dict[str, object]]:
        try:
            return [item.model_dump(mode="json") for item in project_officer_service.outcomes(work_package_id)]
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="read_only") from exc

    @app.post("/integration/v1/project-officer/work-packages/{work_package_id}/submit-for-review")
    def project_officer_submit_for_review(work_package_id: str, request: ProjectOfficerLifecycleRequest) -> dict[str, object]:
        try:
            return project_officer_service.submit_for_review(work_package_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="gaia_local_state") from exc

    @app.post("/integration/v1/project-officer/work-packages/{work_package_id}/approve")
    def project_officer_approve(work_package_id: str, request: ProjectOfficerLifecycleRequest) -> dict[str, object]:
        try:
            return project_officer_service.approve(work_package_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="gaia_local_state") from exc

    @app.post("/integration/v1/project-officer/work-packages/{work_package_id}/reject")
    def project_officer_reject(work_package_id: str, request: ProjectOfficerLifecycleRequest) -> dict[str, object]:
        try:
            return project_officer_service.reject(work_package_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="gaia_local_state") from exc

    @app.post("/integration/v1/project-officer/work-packages/{work_package_id}/expire")
    def project_officer_expire(work_package_id: str, reason: str = Body(default="manual expiry")) -> dict[str, object]:
        try:
            return project_officer_service.expire(work_package_id, reason=reason).model_dump(mode="json")
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="gaia_local_state") from exc

    @app.post("/integration/v1/project-officer/work-packages/{work_package_id}/handoff")
    def project_officer_handoff(work_package_id: str, request: ProjectOfficerHandoffRequest) -> dict[str, object]:
        try:
            return project_officer_service.handoff(work_package_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="manual_handoff_only") from exc

    @app.post("/integration/v1/project-officer/work-packages/{work_package_id}/outcome")
    def project_officer_outcome(work_package_id: str, request: ProjectOfficerOutcomeRequest) -> dict[str, object]:
        try:
            return project_officer_service.record_outcome(work_package_id, request).model_dump(mode="json")
        except Exception as exc:
            raise _project_officer_http_error(exc, resource_type="work_package", resource_id=work_package_id, authority_level="gaia_local_state") from exc

    @app.get("/signing/keys")
    def signing_keys() -> list[dict[str, object]]:
        return trust_service.list_signing_keys()

    @app.post("/signing/keys")
    def create_signing_key(key_name: str = Body(embed=True), activate: bool = Body(default=True, embed=True)) -> dict[str, object]:
        return trust_service.create_signing_key(key_name, activate=activate)

    @app.post("/signing/keys/{key_id}/rotate")
    def rotate_signing_key(key_id: str, next_key_name: str | None = Body(default=None, embed=True)) -> dict[str, object]:
        return trust_service.rotate_signing_key(key_id, next_key_name=next_key_name)

    @app.post("/signing/keys/{key_id}/revoke")
    def revoke_signing_key(key_id: str, reason: str = Body(default="revoked", embed=True)) -> dict[str, object]:
        return trust_service.revoke_signing_key(key_id, reason=reason)

    @app.get("/provenance/manifests")
    def provenance_manifests() -> list[dict[str, object]]:
        return trust_service.list_provenance_manifests()

    @app.post("/provenance/manifests")
    def provenance_manifest_create(request: ProvenanceCreateRequest) -> dict[str, object]:
        return trust_service.create_provenance_manifest(request)

    @app.get("/provenance/manifests/{manifest_id}")
    def provenance_manifest_get(manifest_id: str) -> dict[str, object]:
        try:
            return trust_service.get_provenance_manifest(manifest_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Provenance manifest not found") from exc

    @app.post("/provenance/manifests/{manifest_id}/verify")
    def provenance_manifest_verify(manifest_id: str) -> dict[str, object]:
        try:
            return trust_service.verify_provenance_manifest(manifest_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Provenance manifest not found") from exc

    @app.get("/trust/alerts")
    def trust_alerts() -> list[dict[str, object]]:
        return trust_service.list_trust_alerts()

    @app.post("/trust/alerts/refresh")
    def trust_alerts_refresh() -> list[dict[str, object]]:
        return trust_service.refresh_trust_alerts()

    @app.post("/trust/alerts/{alert_id}/acknowledge")
    def trust_alert_acknowledge(
        alert_id: str,
        reviewer: str = Body(default="manual", embed=True),
        reason: str = Body(default="", embed=True),
    ) -> dict[str, object]:
        try:
            return trust_service.acknowledge_trust_alert(alert_id, reviewer=reviewer, reason=reason)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Trust alert not found") from exc

    @app.get("/integration/v1/status")
    def integration_status() -> dict[str, object]:
        status = workflow_service.integration_status()
        status["output_workspace"] = output_service.summary()
        status["compatibility"] = trust_service.compatibility()
        status["capabilities"] = trust_service.provenance.capability_payload()
        status["trust"] = {
            "action_templates": len(trust_service.list_action_templates()),
            "receipt_chains": len(trust_service.list_receipt_chains()),
            "retention_policies": len(trust_service.list_retention_policies()),
            "alerts": len(trust_service.list_trust_alerts()),
            "provenance_manifests": len(trust_service.list_provenance_manifests()),
            "signing_keys": len(trust_service.list_signing_keys()),
        }
        status["retention_report"] = trust_service.retention_report()
        return status

    @app.get("/integration/v1/projects")
    def integration_projects() -> list[dict[str, object]]:
        return [project.model_dump(mode="json") for project in resolved_settings.projects.values()]

    @app.get("/integration/v1/tasks/summary")
    def integration_tasks_summary(project_id: str | None = None) -> dict[str, object]:
        return workflow_service.task_summary(project_id)

    @app.get("/integration/v1/approvals/summary")
    def integration_approvals_summary(project_id: str | None = None) -> dict[str, object]:
        return workflow_service.approval_summary(project_id)

    @app.get("/integration/v1/briefs/latest")
    def integration_briefs_latest(project_id: str | None = None) -> dict[str, object] | None:
        brief = workflow_service.briefs_latest(project_id)
        return brief.model_dump(mode="json") if brief else None

    @app.get("/integration/v1/actions/summary")
    def integration_actions_summary(project_id: str | None = None) -> dict[str, object]:
        actions = output_service.list_actions(project_id=project_id, limit=500)
        return {
            "project_id": project_id,
            "total": len(actions),
            "proposed": sum(action.status == "proposed" for action in actions),
            "awaiting_approval": sum(action.status == "awaiting_approval" for action in actions),
            "approved": sum(action.status == "approved" for action in actions),
            "completed": sum(action.status == "completed" for action in actions),
            "failed": sum(action.status == "failed" for action in actions),
            "invalidated": sum(action.status == "invalidated" for action in actions),
            "rolled_back": sum(action.status == "rolled_back" for action in actions),
        }

    @app.get("/integration/v1/receipts/latest")
    def integration_latest_receipt() -> dict[str, object] | None:
        receipts = output_service.list_receipts(limit=1)
        return receipts[0].model_dump(mode="json") if receipts else None

    @app.get("/integration/v1/compatibility")
    def integration_compatibility() -> dict[str, object]:
        return trust_service.compatibility()

    return app


app = create_app()
