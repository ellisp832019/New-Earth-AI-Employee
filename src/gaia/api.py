from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from gaia import __version__
from gaia.agent import AgentService
from gaia.config import Settings, load_settings
from gaia.conversation import AskRequest
from gaia.db import Database
from gaia.models import HealthResponse
from gaia.providers import ProviderRegistry
from gaia.service import ProjectService


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    database = Database(resolved_settings.database_path)
    service = ProjectService(resolved_settings, database)
    provider_registry = ProviderRegistry(resolved_settings.model_routing)
    agent_service = AgentService(service, database, provider_registry)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service.audit.record(category="application", operation="startup", outcome="success")
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

    @app.get("/agent/runs")
    def agent_runs(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict[str, object]]:
        return database.list_agent_runs(limit)

    @app.get("/agent/runs/{run_id}")
    def agent_run(run_id: str) -> dict[str, object]:
        run = database.get_agent_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    return app


app = create_app()
