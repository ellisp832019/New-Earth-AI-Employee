from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from gaia import __version__
from gaia.agent import AgentService
from gaia.config import Settings, load_settings
from gaia.conversation import AskRequest
from gaia.db import Database
from gaia.models import HealthResponse
from gaia.output_workspace import (
    OutputActionCreateRequest,
    OutputWorkspaceError,
    OutputWorkspaceService,
    PathSafetyError,
    PermissionManifestCreateRequest,
    PermissionManifestDecisionRequest,
)
from gaia.output_workspace import PermissionDeniedError as OutputPermissionDeniedError
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
    provider_registry = ProviderRegistry(resolved_settings.model_routing)
    agent_service = AgentService(service, database, provider_registry)
    workflow_service = TaskWorkflowService(resolved_settings, database)
    output_service = OutputWorkspaceService(resolved_settings, database)
    trust_service = GAIATrustService(resolved_settings, database)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service.audit.record(category="application", operation="startup", outcome="success")
        trust_service.seed_templates()
        trust_service.seed_retention_policies()
        yield
        database.close()

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

    @app.get("/projects")
    def projects() -> list[dict[str, object]]:
        return [project.model_dump(mode="json") for project in resolved_settings.projects.values()]

    @app.get("/projects/{project_id}")
    def project(project_id: str) -> dict[str, object]:
        try:
            return service.get_project(project_id).model_dump(mode="json")
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

    @app.get("/audit/events")
    def audit_events(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict[str, object]]:
        return database.list_audit_events(limit)

    @app.get("/models/status")
    async def models_status() -> list[dict[str, object]]:
        return [status.model_dump(mode="json") for status in await provider_registry.list_status()]

    @app.get("/models")
    async def models() -> list[dict[str, object]]:
        return [status.model_dump(mode="json") for status in await provider_registry.list_status()]

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

    @app.get("/integration/v1/status")
    def integration_status() -> dict[str, object]:
        status = workflow_service.integration_status()
        status["output_workspace"] = output_service.summary()
        status["compatibility"] = trust_service.compatibility()
        status["trust"] = {
            "action_templates": len(trust_service.list_action_templates()),
            "receipt_chains": len(trust_service.list_receipt_chains()),
            "retention_policies": len(trust_service.list_retention_policies()),
        }
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
