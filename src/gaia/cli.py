from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import typer
import uvicorn
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from gaia import __version__
from gaia.agent import AgentService
from gaia.api import create_app
from gaia.config import load_settings
from gaia.db import Database
from gaia.models import WorkPackageOutcome
from gaia.output_workspace import (
    OutputActionCreateRequest,
    OutputWorkspaceService,
    PermissionManifestCreateRequest,
    PermissionManifestDecisionRequest,
)
from gaia.project_officer import (
    ProjectOfficerHandoffRequest,
    ProjectOfficerLifecycleRequest,
    ProjectOfficerOutcomeRequest,
    ProjectOfficerService,
)
from gaia.provenance import ProvenanceCreateRequest
from gaia.providers import ProviderRegistry
from gaia.reports import write_report
from gaia.service import ProjectService
from gaia.trust import GAIATrustService
from gaia.workflows import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ApprovalRisk,
    DraftCreateRequest,
    DraftReviseRequest,
    DraftType,
    TaskCreateRequest,
    TaskPriority,
    TaskStatus,
    TaskTransitionRequest,
    TaskUpdateRequest,
    TaskWorkflowService,
)

app = typer.Typer(help="GAIA local-first project-control employee")
project_app = typer.Typer(help="Inspect registered projects")
projects_app = typer.Typer(help="List registered projects")
models_app = typer.Typer(help="Model provider status")
agent_app = typer.Typer(help="Conversational agent commands")
agent_runs_app = typer.Typer(help="Agent run history")
tasks_app = typer.Typer(help="GAIA task records")
drafts_app = typer.Typer(help="GAIA draft records")
approvals_app = typer.Typer(help="GAIA approval records")
briefs_app = typer.Typer(help="GAIA daily brief records")
governance_app = typer.Typer(help="NEOS governance context")
permissions_app = typer.Typer(help="Permission manifests and output workspace controls")
actions_app = typer.Typer(help="Permissioned GAIA output actions")
receipts_app = typer.Typer(help="Execution receipts")
templates_app = typer.Typer(help="Versioned action templates")
retention_app = typer.Typer(help="Retention policies and plans")
review_packages_app = typer.Typer(help="Offline review packages")
provenance_app = typer.Typer(help="Provenance manifests and inspection")
signing_app = typer.Typer(help="Local Ed25519 signing keys")
trust_alerts_app = typer.Typer(help="Trust alerts and diagnostics")
project_officer_app = typer.Typer(help="Project Officer planning surfaces")
project_officer_work_package_app = typer.Typer(help="Work package lifecycle commands")
app.add_typer(project_app, name="project")
app.add_typer(projects_app, name="projects")
app.add_typer(models_app, name="models")
app.add_typer(agent_app, name="agent")
agent_app.add_typer(agent_runs_app, name="runs")
app.add_typer(tasks_app, name="tasks")
app.add_typer(drafts_app, name="drafts")
app.add_typer(approvals_app, name="approvals")
app.add_typer(briefs_app, name="briefs")
app.add_typer(governance_app, name="governance")
app.add_typer(permissions_app, name="permissions")
app.add_typer(actions_app, name="actions")
app.add_typer(receipts_app, name="receipts")
app.add_typer(templates_app, name="templates")
app.add_typer(retention_app, name="retention")
app.add_typer(review_packages_app, name="review-packages")
app.add_typer(provenance_app, name="provenance")
app.add_typer(signing_app, name="signing")
app.add_typer(trust_alerts_app, name="alerts")
app.add_typer(project_officer_app, name="project-officer")
project_officer_app.add_typer(project_officer_work_package_app, name="work-package")
console = Console()


def _service(config: Path | None = None) -> ProjectService:
    settings = load_settings(config)
    return ProjectService(settings, Database(settings.database_path))


def _bundle(config: Path | None = None) -> tuple[ProjectService, Database, ProviderRegistry, AgentService]:
    settings = load_settings(config)
    database = Database(settings.database_path)
    service = ProjectService(settings, database)
    registry = ProviderRegistry(settings.model_routing)
    agent = AgentService(service, database, registry)
    return service, database, registry, agent


def _workflow_service(config: Path | None = None) -> TaskWorkflowService:
    settings = load_settings(config)
    return TaskWorkflowService(settings, Database(settings.database_path))


def _workspace_service(config: Path | None = None) -> OutputWorkspaceService:
    settings = load_settings(config)
    return OutputWorkspaceService(settings, Database(settings.database_path))


def _trust_service(config: Path | None = None) -> GAIATrustService:
    settings = load_settings(config)
    return GAIATrustService(settings, Database(settings.database_path))


def _project_officer_service(config: Path | None = None) -> ProjectOfficerService:
    settings = load_settings(config)
    service = ProjectService(settings, Database(settings.database_path))
    return ProjectOfficerService(service)


def _print_models(records: Sequence[BaseModel]) -> None:
    if not records:
        console.print("No records found.")
        return
    console.print_json(json.dumps([record.model_dump(mode="json") for record in records]))


def _print_model(record: BaseModel) -> None:
    console.print_json(json.dumps(record.model_dump(mode="json")))


def _safe_output_path(output: Path) -> Path:
    allowed_root = Path("data/reports").resolve()
    resolved = output.resolve()
    if allowed_root not in resolved.parents and resolved != allowed_root:
        raise typer.BadParameter("output must be inside data/reports")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def _render_ask_markdown(response: dict[str, object]) -> str:
    evidence = response.get("evidence", [])
    if isinstance(evidence, list):
        evidence_lines = "\n".join(
            f"- {item.get('source_path', '')}: {item.get('snippet', '')}" for item in evidence if isinstance(item, dict)
        )
    else:
        evidence_lines = ""
    warnings = response.get("warnings", [])
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) if isinstance(warnings, list) else ""
    return (
        f"# Ask Result\n\n"
        f"- Run ID: `{response.get('run_id', '')}`\n"
        f"- Project ID: `{response.get('project_id', '')}`\n"
        f"- Snapshot ID: `{response.get('snapshot_id', '')}`\n"
        f"- Provider: `{response.get('provider', '')}`\n"
        f"- Model: `{response.get('model_name', '')}`\n"
        f"- Confidence: `{response.get('confidence', '')}`\n\n"
        f"## Answer\n\n{response.get('answer', '')}\n\n"
        f"## Evidence\n\n{evidence_lines or '- None'}\n\n"
        f"## Warnings\n\n{warning_lines or '- None'}\n"
    )


@app.command()
def doctor(config: Path | None = typer.Option(None, help="Path to project configuration")) -> None:
    """Check configuration, database, Git and registered project roots."""
    settings = load_settings(config)
    database = Database(settings.database_path)
    registry = ProviderRegistry(settings.model_routing)
    rows = []
    rows.append(("GAIA version", __version__, True))
    rows.append(("Configuration", str(settings.config_path), settings.config_path.exists()))
    rows.append(("Database", str(settings.database_path), True))
    rows.append(("SQLite FTS5", str(database.fts5_available), True))
    rows.append(("Git executable", shutil.which("git") or "not found", shutil.which("git") is not None))
    rows.append(("Model routing", str(settings.model_routing_path), settings.model_routing_path.exists() or not settings.model_routing.enabled))
    for project in settings.projects.values():
        rows.append((f"Project {project.project_id}", str(project.root), project.root.exists()))
    for status in asyncio.run(registry.list_status()):
        rows.append((f"Model {status.provider}", status.details or "ok", status.available))
    table = Table(title="GAIA Doctor")
    table.add_column("Check")
    table.add_column("Value")
    table.add_column("Status")
    for name, value, ok in rows:
        table.add_row(name, value, "PASS" if ok else "WARN")
    console.print(table)
    database.close()


@projects_app.command("list")
def projects_list(config: Path | None = typer.Option(None)) -> None:
    settings = load_settings(config)
    table = Table(title="Registered projects")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Root")
    table.add_column("Access")
    for project in settings.projects.values():
        table.add_row(project.project_id, project.name, str(project.root), project.access)
    console.print(table)


@project_app.command("show")
def project_show(project_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _service(config)
    try:
        console.print_json(service.get_project(project_id).model_dump_json())
    finally:
        service.database.close()


@project_app.command("scan")
def project_scan(project_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _service(config)
    try:
        documents = service.scan(project_id)
        indexed = sum(item["indexing_status"] == "indexed" for item in documents)
        skipped = sum(item["indexing_status"] == "skipped" for item in documents)
        failed = sum(item["indexing_status"] == "failed" for item in documents)
        console.print(f"Scanned {len(documents)} documents: {indexed} indexed, {skipped} skipped, {failed} failed")
    finally:
        service.database.close()


@project_app.command("snapshot")
def project_snapshot(project_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _service(config)
    try:
        snapshot = service.snapshot(project_id)
        console.print_json(snapshot.model_dump_json())
    finally:
        service.database.close()


@project_app.command("search")
def project_search(
    project_id: str,
    query: str,
    limit: int = typer.Option(20, min=1, max=100),
    config: Path | None = typer.Option(None),
) -> None:
    service = _service(config)
    try:
        results = service.search(project_id, query, limit)
        table = Table(title=f"Search: {query}")
        table.add_column("Path")
        table.add_column("Snippet")
        for result in results:
            table.add_row(result.relative_path, result.snippet)
        console.print(table)
    finally:
        service.database.close()


@project_app.command("report")
def project_report(
    project_id: str,
    format: str = typer.Option("markdown", help="markdown or json"),
    output: Path | None = typer.Option(None, help="Optional output file"),
    config: Path | None = typer.Option(None),
) -> None:
    if format not in {"markdown", "json"}:
        raise typer.BadParameter("format must be markdown or json")
    service = _service(config)
    try:
        snapshot = service.database.latest_snapshot(project_id) or service.snapshot(project_id)
        if output:
            path = write_report(snapshot, output, format)
            console.print(f"Report written to {path}")
        else:
            console.print(service.foundation_report(project_id, format))
    finally:
        service.database.close()


@models_app.command("status")
def models_status(config: Path | None = typer.Option(None)) -> None:
    _service, database, registry, _agent = _bundle(config)
    try:
        table = Table(title="Model Status")
        table.add_column("Provider")
        table.add_column("Available")
        table.add_column("Model")
        table.add_column("Details")
        for status in asyncio.run(registry.list_status()):
            table.add_row(status.provider, str(status.available), status.model_name or "", status.details or "")
        console.print(table)
    finally:
        database.close()


@models_app.command("list")
def models_list(config: Path | None = typer.Option(None)) -> None:
    models_status(config)


@agent_runs_app.command("list")
def agent_runs_list(limit: int = typer.Option(100, min=1, max=1000), config: Path | None = typer.Option(None)) -> None:
    _service, database, _registry, _agent = _bundle(config)
    try:
        console.print_json(json.dumps(database.list_agent_runs(limit=limit)))
    finally:
        database.close()


@agent_runs_app.command("show")
def agent_runs_show(run_id: str, config: Path | None = typer.Option(None)) -> None:
    _service, database, _registry, _agent = _bundle(config)
    try:
        run = database.get_agent_run(run_id)
        if not run:
            raise typer.BadParameter("Run not found")
        console.print_json(json.dumps(run))
    finally:
        database.close()


@governance_app.command("context")
def governance_context(
    project_id: str | None = typer.Option(None),
    finding_id: str | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _service(config)
    try:
        _print_model(service.governance_context(project_id=project_id, finding_id=finding_id))
    finally:
        service.close()


@governance_app.command("status")
def governance_status(project_id: str | None = typer.Option(None), config: Path | None = typer.Option(None)) -> None:
    service = _service(config)
    try:
        _print_model(service.governance_status(project_id=project_id))
    finally:
        service.close()


@governance_app.command("findings")
def governance_findings(project_id: str | None = typer.Option(None), config: Path | None = typer.Option(None)) -> None:
    service = _service(config)
    try:
        _print_model(service.governance_findings(project_id=project_id))
    finally:
        service.close()


@governance_app.command("project")
def governance_project(project_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _service(config)
    try:
        _print_model(service.governance_project(project_id))
    finally:
        service.close()


@governance_app.command("snapshot")
def governance_snapshot(config: Path | None = typer.Option(None)) -> None:
    service = _service(config)
    try:
        _print_model(service.governance_snapshot())
    finally:
        service.close()


@governance_app.command("brief")
def governance_brief(project_id: str | None = typer.Option(None), config: Path | None = typer.Option(None)) -> None:
    service = _service(config)
    try:
        console.print(service.governance_brief(project_id=project_id).markdown)
    finally:
        service.close()


@governance_app.command("work-package")
def governance_work_package(
    finding_id: str,
    project_id: str | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _service(config)
    try:
        _print_model(service.governance_work_package_preview(finding_id, project_id=project_id))
    finally:
        service.close()


@app.command()
def ask(
    project_id: str,
    question: str,
    provider: str | None = typer.Option(None),
    model: str | None = typer.Option(None),
    evidence_limit: int = typer.Option(8, min=1, max=20),
    format: str = typer.Option("markdown", help="markdown or json"),
    output: Path | None = typer.Option(None, help="Optional output file in data/reports"),
    refresh_snapshot: bool = typer.Option(False),
    deterministic_only: bool = typer.Option(False),
    config: Path | None = typer.Option(None),
) -> None:
    if format not in {"markdown", "json"}:
        raise typer.BadParameter("format must be markdown or json")
    _service, database, _registry, agent = _bundle(config)
    try:
        response = asyncio.run(
            agent.ask(
                project_id,
                question,
                provider=provider,
                model=model,
                evidence_limit=evidence_limit,
                refresh_snapshot=refresh_snapshot,
                deterministic_only=deterministic_only,
            )
        )
        payload = response.model_dump(mode="json")
        if output:
            target = _safe_output_path(output)
            if format == "json":
                target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            else:
                target.write_text(_render_ask_markdown(payload), encoding="utf-8")
            console.print(f"Ask response written to {target}")
        else:
            if format == "json":
                console.print_json(json.dumps(payload))
            else:
                console.print(_render_ask_markdown(payload))
    finally:
        database.close()


@app.command()
def serve(
    host: str | None = typer.Option(None),
    port: int | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    """Start the local FastAPI service."""
    settings = load_settings(config)
    uvicorn.run(create_app(settings), host=host or settings.api_host, port=port or settings.api_port)


@project_officer_app.command("capabilities")
def project_officer_capabilities(config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(service.capabilities())
    finally:
        service.database.close()


@project_officer_app.command("portfolio")
def project_officer_portfolio(config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(service.portfolio())
    finally:
        service.database.close()


@project_officer_app.command("projects")
def project_officer_projects(config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(service.projects())
    finally:
        service.database.close()


@project_officer_app.command("health")
def project_officer_health(project_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(service.project_health(project_id))
    finally:
        service.database.close()


@project_officer_app.command("health-snapshots")
def project_officer_health_snapshots(
    project_id: str,
    limit: int = typer.Option(100, min=1, max=500),
    offset: int = typer.Option(0, min=0),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(service.project_health_snapshots(project_id)[offset : offset + limit])
    finally:
        service.database.close()


@project_officer_app.command("health-snapshot")
def project_officer_health_snapshot(snapshot_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        snapshot = service.project_health_snapshot(snapshot_id)
        if snapshot is None:
            raise typer.BadParameter("Snapshot not found")
        _print_model(snapshot)
    finally:
        service.database.close()


@project_officer_app.command("change-portfolio")
def project_officer_change_portfolio(config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(service.change_portfolio())
    finally:
        service.database.close()


@project_officer_app.command("changes")
def project_officer_changes(
    project_id: str,
    severity: str | None = typer.Option(None),
    direction: str | None = typer.Option(None),
    change_type: str | None = typer.Option(None),
    status: str | None = typer.Option(None),
    limit: int = typer.Option(100, min=1, max=500),
    offset: int = typer.Option(0, min=0),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(
            service.change_findings(
                project_id,
                severity=severity,
                direction=direction,
                change_type=change_type,
                status=status,
                limit=limit,
                offset=offset,
            )
        )
    finally:
        service.database.close()


@project_officer_app.command("change")
def project_officer_change(finding_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        finding = service.change_finding(finding_id)
        if finding is None:
            raise typer.BadParameter("Change finding not found")
        _print_model(finding)
    finally:
        service.database.close()


@project_officer_app.command("recent-changes")
def project_officer_recent_changes(
    project_id: str | None = typer.Option(None),
    limit: int = typer.Option(100, min=1, max=500),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(service.recent_change_findings(project_id=project_id, limit=limit))
    finally:
        service.database.close()


@project_officer_app.command("recommendation-portfolio")
def project_officer_recommendation_portfolio(config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(service.recommendation_portfolio())
    finally:
        service.database.close()


@project_officer_app.command("recommendations")
def project_officer_recommendations(
    project_id: str | None = typer.Option(None),
    priority_tier: str | None = typer.Option(None),
    lifecycle_state: str | None = typer.Option(None),
    blocked_only: bool = typer.Option(False),
    limit: int = typer.Option(100, min=1, max=500),
    offset: int = typer.Option(0, min=0),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(
            service.recommendations(
                project_id=project_id,
                priority_tier=priority_tier,
                lifecycle_state=lifecycle_state,
                blocked_only=blocked_only,
                limit=limit,
                offset=offset,
            )
        )
    finally:
        service.database.close()


@project_officer_app.command("recommendation")
def project_officer_recommendation(recommendation_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        recommendation = service.recommendation(recommendation_id)
        if recommendation is None:
            raise typer.BadParameter("Recommendation not found")
        _print_model(recommendation)
    finally:
        service.database.close()


@project_officer_app.command("work-packages")
def project_officer_work_packages(
    project_id: str | None = typer.Option(None),
    approval_state: str | None = typer.Option(None),
    staleness_state: str | None = typer.Option(None),
    risk_classification: str | None = typer.Option(None),
    limit: int = typer.Option(100, min=1, max=500),
    offset: int = typer.Option(0, min=0),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(
            service.work_packages(
                project_id=project_id,
                approval_state=approval_state,
                staleness_state=staleness_state,
                risk_classification=risk_classification,
                limit=limit,
                offset=offset,
            )
        )
    finally:
        service.database.close()


@project_officer_work_package_app.command("show")
def project_officer_work_package_show(work_package_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        package = service.work_package(work_package_id)
        if package is None:
            raise typer.BadParameter("Work package not found")
        _print_model(package)
    finally:
        service.database.close()


@project_officer_work_package_app.command("summary")
def project_officer_work_package_summary(work_package_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        console.print_json(json.dumps(service.work_package_summary(work_package_id)))
    finally:
        service.database.close()


@project_officer_work_package_app.command("prompt")
def project_officer_work_package_prompt(
    work_package_id: str,
    revision_number: int | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        console.print_json(json.dumps(service.work_package_prompt(work_package_id, revision_number=revision_number)))
    finally:
        service.database.close()


@project_officer_work_package_app.command("revisions")
def project_officer_work_package_revisions(work_package_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(service.work_package_revisions(work_package_id))
    finally:
        service.database.close()


@project_officer_work_package_app.command("revision")
def project_officer_work_package_revision(revision_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        revision = service.work_package_revision(revision_id)
        if revision is None:
            raise typer.BadParameter("Revision not found")
        _print_model(revision)
    finally:
        service.database.close()


@project_officer_work_package_app.command("approval-decisions")
def project_officer_work_package_approval_decisions(
    work_package_id: str,
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(service.approval_decisions(work_package_id))
    finally:
        service.database.close()


@project_officer_work_package_app.command("handoffs")
def project_officer_work_package_handoffs(work_package_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(service.handoffs(work_package_id))
    finally:
        service.database.close()


@project_officer_work_package_app.command("outcomes")
def project_officer_work_package_outcomes(work_package_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _project_officer_service(config)
    try:
        _print_models(service.outcomes(work_package_id))
    finally:
        service.database.close()


@project_officer_work_package_app.command("submit-for-review")
def project_officer_work_package_submit_for_review(
    work_package_id: str,
    revision_number: int = typer.Option(..., min=1),
    actor: str = typer.Option("manual"),
    human_note: str | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(
            service.submit_for_review(
                work_package_id,
                ProjectOfficerLifecycleRequest(revision_number=revision_number, actor=actor, human_note=human_note),
            )
        )
    finally:
        service.database.close()


@project_officer_work_package_app.command("approve")
def project_officer_work_package_approve(
    work_package_id: str,
    revision_number: int = typer.Option(..., min=1),
    actor: str = typer.Option("manual"),
    human_note: str | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(
            service.approve(
                work_package_id,
                ProjectOfficerLifecycleRequest(revision_number=revision_number, actor=actor, human_note=human_note),
            )
        )
    finally:
        service.database.close()


@project_officer_work_package_app.command("reject")
def project_officer_work_package_reject(
    work_package_id: str,
    revision_number: int = typer.Option(..., min=1),
    actor: str = typer.Option("manual"),
    human_note: str | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(
            service.reject(
                work_package_id,
                ProjectOfficerLifecycleRequest(revision_number=revision_number, actor=actor, human_note=human_note),
            )
        )
    finally:
        service.database.close()


@project_officer_work_package_app.command("expire")
def project_officer_work_package_expire(
    work_package_id: str,
    reason: str = typer.Option("manual expiry"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(service.expire(work_package_id, reason=reason))
    finally:
        service.database.close()


@project_officer_work_package_app.command("handoff")
def project_officer_work_package_handoff(
    work_package_id: str,
    revision_number: int = typer.Option(..., min=1),
    approved_by: str = typer.Option("manual"),
    next_manual_action: str = typer.Option("Copy the approved Codex prompt into Codex."),
    rollback_reference: str = typer.Option("Return to the recorded baseline commit or last approved revision."),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(
            service.handoff(
                work_package_id,
                ProjectOfficerHandoffRequest(
                    revision_number=revision_number,
                    approved_by=approved_by,
                    next_manual_action=next_manual_action,
                    rollback_reference=rollback_reference,
                ),
            )
        )
    finally:
        service.database.close()


@project_officer_work_package_app.command("outcome")
def project_officer_work_package_outcome(
    work_package_id: str,
    revision_number: int = typer.Option(..., min=1),
    outcome: WorkPackageOutcome = typer.Option(...),
    actor: str = typer.Option("manual"),
    note: str | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _project_officer_service(config)
    try:
        _print_model(
            service.record_outcome(
                work_package_id,
                ProjectOfficerOutcomeRequest(
                    revision_number=revision_number,
                    outcome=outcome,
                    actor=actor,
                    note=note,
                ),
            )
        )
    finally:
        service.database.close()


@tasks_app.command("list")
def tasks_list(
    project_id: str | None = typer.Option(None),
    status: str | None = typer.Option(None),
    priority: str | None = typer.Option(None),
    limit: int = typer.Option(100, min=1, max=500),
    offset: int = typer.Option(0, min=0),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        _print_models(service.list_tasks(project_id=project_id, status=status, priority=priority, limit=limit, offset=offset))
    finally:
        service.close()


@tasks_app.command("show")
def tasks_show(task_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.get_task(task_id))
    finally:
        service.close()


@tasks_app.command("create")
def tasks_create(
    title: str = typer.Argument(...),
    project_id: str = typer.Option(...),
    description: str = typer.Option(""),
    priority: str = typer.Option("normal"),
    category: str = typer.Option("general"),
    source_type: str = typer.Option("manual"),
    source_identifier: str | None = typer.Option(None),
    source_agent_run_id: str | None = typer.Option(None),
    evidence_reference: list[str] | None = typer.Option(None),
    dependency_task_id: list[str] | None = typer.Option(None),
    blocker_description: str | None = typer.Option(None),
    assigned_to: str | None = typer.Option(None),
    completion_criteria: str = typer.Option(""),
    approval_requirement: bool = typer.Option(False),
    tag: list[str] | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        task = service.create_task(
            TaskCreateRequest(
                title=title,
                project_id=project_id,
                description=description,
                priority=cast(TaskPriority, priority),
                category=category,
                source_type=source_type,
                source_identifier=source_identifier,
                source_agent_run_id=source_agent_run_id,
                evidence_references=evidence_reference or [],
                dependency_task_ids=dependency_task_id or [],
                blocker_description=blocker_description,
                assigned_to=assigned_to,
                completion_criteria=completion_criteria,
                approval_requirement=approval_requirement,
                tags=tag or [],
            )
        )
        _print_model(task)
    finally:
        service.close()


@tasks_app.command("from-run")
def tasks_from_run(run_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.create_task_from_run(run_id))
    finally:
        service.close()


@tasks_app.command("accept")
def tasks_accept(task_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.accept_task(task_id))
    finally:
        service.close()


@tasks_app.command("transition")
def tasks_transition(
    task_id: str,
    status: str = typer.Argument(...),
    reason: str | None = typer.Option(None),
    completion_evidence: list[str] | None = typer.Option(None),
    manual_override_reason: str | None = typer.Option(None),
    actor: str = typer.Option("manual"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        task = service.get_task(task_id)
        _print_model(
            service.transition_task(
                task_id,
                TaskTransitionRequest(
                    version=task.version,
                    status=cast(TaskStatus, status),
                    reason=reason,
                    completion_evidence=completion_evidence or None,
                    manual_override_reason=manual_override_reason,
                    actor=actor,
                ),
            )
        )
    finally:
        service.close()


@tasks_app.command("update")
def tasks_update(
    task_id: str,
    version: int = typer.Option(...),
    title: str | None = typer.Option(None),
    description: str | None = typer.Option(None),
    priority: str | None = typer.Option(None),
    category: str | None = typer.Option(None),
    assigned_to: str | None = typer.Option(None),
    blocker_description: str | None = typer.Option(None),
    completion_criteria: str | None = typer.Option(None),
    approval_requirement: bool | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        _print_model(
            service.update_task(
                task_id,
                TaskUpdateRequest(
                    version=version,
                    title=title,
                    description=description,
                    priority=cast(TaskPriority, priority),
                    category=category,
                    assigned_to=assigned_to,
                    blocker_description=blocker_description,
                    completion_criteria=completion_criteria,
                    approval_requirement=approval_requirement,
                ),
            )
        )
    finally:
        service.close()


@tasks_app.command("cancel")
def tasks_cancel(task_id: str, reason: str | None = typer.Option(None), config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.cancel_task(task_id, reason=reason))
    finally:
        service.close()


@tasks_app.command("history")
def tasks_history(task_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_models(service.task_history(task_id))
    finally:
        service.close()


@drafts_app.command("list")
def drafts_list(
    project_id: str | None = typer.Option(None),
    status: str | None = typer.Option(None),
    limit: int = typer.Option(100, min=1, max=500),
    offset: int = typer.Option(0, min=0),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        _print_models(service.list_drafts(project_id=project_id, status=status, limit=limit, offset=offset))
    finally:
        service.close()


@drafts_app.command("show")
def drafts_show(draft_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.get_draft(draft_id))
    finally:
        service.close()


@drafts_app.command("create")
def drafts_create(
    title: str = typer.Argument(...),
    project_id: str = typer.Option(...),
    draft_type: str = typer.Option("generic_markdown"),
    content: str = typer.Option(""),
    source_task_id: str | None = typer.Option(None),
    source_agent_run_id: str | None = typer.Option(None),
    approval_requirement: bool = typer.Option(False),
    author: str = typer.Option("manual"),
    change_reason: str = typer.Option("initial draft"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        draft, _revision = service.create_draft(
            DraftCreateRequest(
                title=title,
                draft_type=cast(DraftType, draft_type),
                project_id=project_id,
                content=content,
                source_task_id=source_task_id,
                source_agent_run_id=source_agent_run_id,
                approval_requirement=approval_requirement,
                author=author,
                change_reason=change_reason,
            )
        )
        _print_model(draft)
    finally:
        service.close()


@drafts_app.command("revise")
def drafts_revise(
    draft_id: str,
    version: int = typer.Option(...),
    content: str = typer.Option(...),
    author: str = typer.Option("manual"),
    change_reason: str = typer.Option("revision"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        draft, _revision = service.revise_draft(
            draft_id,
            DraftReviseRequest(version=version, content=content, author=author, change_reason=change_reason),
        )
        _print_model(draft)
    finally:
        service.close()


@drafts_app.command("submit")
def drafts_submit(draft_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.submit_draft_for_review(draft_id))
    finally:
        service.close()


@drafts_app.command("reject")
def drafts_reject(draft_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.reject_draft(draft_id))
    finally:
        service.close()


@drafts_app.command("supersede")
def drafts_supersede(draft_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.supersede_draft(draft_id))
    finally:
        service.close()


@drafts_app.command("revisions")
def drafts_revisions(draft_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_models(service.draft_revisions(draft_id))
    finally:
        service.close()


@approvals_app.command("list")
def approvals_list(
    project_id: str | None = typer.Option(None),
    status: str | None = typer.Option(None),
    limit: int = typer.Option(100, min=1, max=500),
    offset: int = typer.Option(0, min=0),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        _print_models(service.list_approvals(project_id=project_id, status=status, limit=limit, offset=offset))
    finally:
        service.close()


@approvals_app.command("show")
def approvals_show(approval_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.get_approval(approval_id))
    finally:
        service.close()


@approvals_app.command("create")
def approvals_create(
    title: str = typer.Argument(...),
    project_id: str = typer.Option(...),
    description: str = typer.Option(""),
    request_type: str = typer.Option("manual"),
    source_task_id: str | None = typer.Option(None),
    source_draft_id: str | None = typer.Option(None),
    requesting_source: str = typer.Option("manual"),
    proposed_action: str = typer.Option(""),
    exact_target_description: str = typer.Option(""),
    write_boundary: str = typer.Option("gaia-local"),
    risk_level: str = typer.Option("low"),
    preview_summary: str = typer.Option(""),
    approved_content_hash: str = typer.Option(""),
    reviewer: str | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        _print_model(
            service.create_approval(
                ApprovalCreateRequest(
                    title=title,
                    project_id=project_id,
                    description=description,
                    request_type=request_type,
                    source_task_id=source_task_id,
                    source_draft_id=source_draft_id,
                    requesting_source=requesting_source,
                    proposed_action=proposed_action,
                    exact_target_description=exact_target_description,
                    write_boundary=write_boundary,
                    risk_level=cast(ApprovalRisk, risk_level),
                    preview_summary=preview_summary,
                    approved_content_hash=approved_content_hash,
                    reviewer=reviewer,
                )
            )
        )
    finally:
        service.close()


@approvals_app.command("approve")
def approvals_approve(
    approval_id: str,
    version: int = typer.Option(...),
    reviewer: str = typer.Option("manual"),
    decision_reason: str = typer.Option("approved for manual use"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.approve(approval_id, ApprovalDecisionRequest(version=version, reviewer=reviewer, decision_reason=decision_reason)))
    finally:
        service.close()


@approvals_app.command("reject")
def approvals_reject(
    approval_id: str,
    version: int = typer.Option(...),
    reviewer: str = typer.Option("manual"),
    decision_reason: str = typer.Option("rejected"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.reject_approval(approval_id, ApprovalDecisionRequest(version=version, reviewer=reviewer, decision_reason=decision_reason)))
    finally:
        service.close()


@approvals_app.command("cancel")
def approvals_cancel(
    approval_id: str,
    version: int = typer.Option(...),
    reviewer: str = typer.Option("manual"),
    decision_reason: str = typer.Option("cancelled"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.cancel_approval(approval_id, ApprovalDecisionRequest(version=version, reviewer=reviewer, decision_reason=decision_reason)))
    finally:
        service.close()


@approvals_app.command("refresh-validation")
def approvals_refresh_validation(approval_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.refresh_approval_validation(approval_id))
    finally:
        service.close()


@briefs_app.command("daily")
def briefs_daily(project_id: str | None = typer.Option(None), config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        project = project_id
        if not project:
            project = next(iter(service.settings.projects.keys()), None)
        if not project:
            raise typer.BadParameter("project_id is required when no projects are configured")
        _print_model(service.daily_brief(project))
    finally:
        service.close()


@briefs_app.command("list")
def briefs_list(project_id: str | None = typer.Option(None), limit: int = typer.Option(100, min=1, max=500), offset: int = typer.Option(0, min=0), config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_models(service.list_briefs(project_id=project_id, limit=limit, offset=offset))
    finally:
        service.close()


@briefs_app.command("show")
def briefs_show(brief_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workflow_service(config)
    try:
        _print_model(service.get_brief(brief_id))
    finally:
        service.close()


@permissions_app.command("list")
def permissions_list(config: Path | None = typer.Option(None)) -> None:
    service = _workspace_service(config)
    try:
        _print_models(service.list_permission_manifests())
    finally:
        service.database.close()


@permissions_app.command("show")
def permissions_show(manifest_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workspace_service(config)
    try:
        _print_model(service.get_permission_manifest(manifest_id))
    finally:
        service.database.close()


@permissions_app.command("validate")
def permissions_validate(manifest_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workspace_service(config)
    try:
        console.print_json(json.dumps(service.validate_permission_manifest(manifest_id)))
    finally:
        service.database.close()


@permissions_app.command("create")
def permissions_create(
    name: str,
    allowed_target_root: list[str] = typer.Option([], "--allowed-target-root"),
    allowed_action_type: list[str] = typer.Option([], "--allowed-action-type"),
    allowed_file_extension: list[str] = typer.Option([], "--allowed-file-extension"),
    manifest_version: int = typer.Option(1, hidden=True),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workspace_service(config)
    try:
        request = PermissionManifestCreateRequest(
            name=name,
            allowed_target_roots=allowed_target_root,
            allowed_action_types=cast(Any, allowed_action_type),
            allowed_file_extensions=allowed_file_extension,
        )
        _print_model(service.create_permission_manifest(request))
    finally:
        service.database.close()


@permissions_app.command("review")
def permissions_review(
    manifest_id: str,
    version: int = typer.Option(...),
    reviewer: str = typer.Option("manual"),
    notes: str = typer.Option("manual review"),
    enabled: bool = typer.Option(True),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workspace_service(config)
    try:
        _print_model(
            service.update_permission_manifest(
                manifest_id,
                PermissionManifestDecisionRequest(version=version, reviewer=reviewer, review_notes=notes, enabled=enabled),
            )
        )
    finally:
        service.database.close()


@actions_app.command("list")
def actions_list(
    project_id: str | None = typer.Option(None),
    status: str | None = typer.Option(None),
    limit: int = typer.Option(100, min=1, max=500),
    offset: int = typer.Option(0, min=0),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workspace_service(config)
    try:
        _print_models(service.list_actions(project_id=project_id, status=status, limit=limit, offset=offset))
    finally:
        service.database.close()


@actions_app.command("show")
def actions_show(action_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workspace_service(config)
    try:
        _print_model(service.get_action(action_id))
    finally:
        service.database.close()


@actions_app.command("preview")
def actions_preview(action_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workspace_service(config)
    try:
        console.print_json(
            json.dumps(
                {
                    "action": service.get_action(action_id).model_dump(mode="json"),
                    "previews": [preview.model_dump(mode="json") for preview in service.action_previews(action_id)],
                }
            )
        )
    finally:
        service.database.close()


@actions_app.command("request-approval")
def actions_request_approval(
    action_id: str,
    reviewer: str = typer.Option("manual"),
    decision_reason: str = typer.Option("requested"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workspace_service(config)
    try:
        _print_model(service.request_approval(action_id, reviewer=reviewer, decision_reason=decision_reason))
    finally:
        service.database.close()


@actions_app.command("approve")
def actions_approve(
    action_id: str,
    reviewer: str = typer.Option("manual"),
    decision_reason: str = typer.Option("Approved for manual use"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workspace_service(config)
    try:
        _print_model(service.approve_action(action_id, reviewer=reviewer, decision_reason=decision_reason))
    finally:
        service.database.close()


@actions_app.command("execute")
def actions_execute(
    action_id: str,
    confirm: bool = typer.Option(False),
    operator: str = typer.Option("manual"),
    config: Path | None = typer.Option(None),
) -> None:
    if not confirm:
        raise typer.BadParameter("--confirm is required to execute an action")
    service = _workspace_service(config)
    try:
        action, receipt = service.execute_action(action_id, confirmation_token=action_id, operator=operator)
        console.print_json(json.dumps({"action": action.model_dump(mode="json"), "receipt": receipt.model_dump(mode="json")}))
    finally:
        service.database.close()


@actions_app.command("rollback")
def actions_rollback(
    action_id: str,
    confirm: bool = typer.Option(False),
    operator: str = typer.Option("manual"),
    config: Path | None = typer.Option(None),
) -> None:
    if not confirm:
        raise typer.BadParameter("--confirm is required to rollback an action")
    service = _workspace_service(config)
    try:
        action, rollback = service.rollback_action(action_id, confirmation_token=action_id, operator=operator)
        console.print_json(json.dumps({"action": action.model_dump(mode="json"), "rollback": rollback.model_dump(mode="json")}))
    finally:
        service.database.close()


@actions_app.command("cancel")
def actions_cancel(
    action_id: str,
    reason: str = typer.Option("cancelled"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workspace_service(config)
    try:
        _print_model(service.cancel_action(action_id, reason))
    finally:
        service.database.close()


@actions_app.command("create")
def actions_create(
    title: str,
    project_id: str,
    manifest_id: str,
    target_path: str,
    action_type: str = typer.Option("create_generated_document"),
    content: str = typer.Option(""),
    content_source: str = typer.Option("manual"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _workspace_service(config)
    try:
        request = OutputActionCreateRequest(
            action_type=cast(Any, action_type),
            title=title,
            project_id=project_id,
            manifest_id=manifest_id,
            target_path=target_path,
            content=content or None,
            content_source=cast(Any, content_source),
        )
        _print_model(service.create_action(request))
    finally:
        service.database.close()


@receipts_app.command("list")
def receipts_list(limit: int = typer.Option(100, min=1, max=500), offset: int = typer.Option(0, min=0), config: Path | None = typer.Option(None)) -> None:
    service = _workspace_service(config)
    try:
        _print_models(service.list_receipts(limit=limit, offset=offset))
    finally:
        service.database.close()


@receipts_app.command("show")
def receipts_show(receipt_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _workspace_service(config)
    try:
        _print_model(service.get_receipt(receipt_id))
    finally:
        service.database.close()


@receipts_app.command("verify")
def receipts_verify(receipt_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.verify_receipt(receipt_id).model_dump(mode="json")))
    finally:
        service.database.close()


@receipts_app.command("verify-chain")
def receipts_verify_chain(chain_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.verify_chain(chain_id)))
    finally:
        service.database.close()


@receipts_app.command("export")
def receipts_export(receipt_id: str, output: Path | None = typer.Option(None), config: Path | None = typer.Option(None)) -> None:
    service = _workspace_service(config)
    try:
        receipt = service.get_receipt(receipt_id)
        payload = receipt.model_dump(mode="json")
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            console.print(f"Receipt exported to {output}")
        else:
            console.print_json(json.dumps(payload))
    finally:
        service.database.close()


@receipts_app.command("chains")
def receipts_chains(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.list_receipt_chains()))
    finally:
        service.database.close()


@receipts_app.command("export-chain")
def receipts_export_chain(chain_id: str, output: Path | None = typer.Option(None), config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        payload = service.get_receipt_chain(chain_id)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            console.print(f"Receipt chain exported to {output}")
        else:
            console.print_json(json.dumps(payload))
    finally:
        service.database.close()


@templates_app.command("list")
def templates_list(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps([template.model_dump(mode="json") for template in service.list_action_templates()]))
    finally:
        service.database.close()


@templates_app.command("show")
def templates_show(template_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(service.get_action_template(template_id).model_dump_json())
    finally:
        service.database.close()


@templates_app.command("propose")
def templates_propose(
    template_id: str,
    action_type: str = typer.Option("create_generated_document"),
    title: str = typer.Option("Template proposal"),
    project_id: str = typer.Option("microgrow-v1"),
    manifest_id: str = typer.Option(""),
    target_path: str = typer.Option("workspace/approved_outputs/template.txt"),
    content: str = typer.Option("template content"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _trust_service(config)
    try:
        request = OutputActionCreateRequest(
            action_type=cast(Any, action_type),
            title=title,
            project_id=project_id,
            manifest_id=manifest_id or template_id,
            target_path=target_path,
            content=content,
            content_source="manual",
        )
        console.print_json(json.dumps(service.template_propose(template_id, request)))
    finally:
        service.database.close()


@templates_app.command("preview")
def templates_preview(
    template_id: str,
    action_type: str = typer.Option("create_generated_document"),
    title: str = typer.Option("Template preview"),
    project_id: str = typer.Option("microgrow-v1"),
    manifest_id: str = typer.Option(""),
    target_path: str = typer.Option("workspace/approved_outputs/template.txt"),
    content: str = typer.Option("template content"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _trust_service(config)
    try:
        request = OutputActionCreateRequest(
            action_type=cast(Any, action_type),
            title=title,
            project_id=project_id,
            manifest_id=manifest_id or template_id,
            target_path=target_path,
            content=content,
            content_source="manual",
        )
        console.print_json(json.dumps(service.template_preview(template_id, request)))
    finally:
        service.database.close()


@retention_app.command("policies")
def retention_policies(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps([policy.model_dump(mode="json") for policy in service.list_retention_policies()]))
    finally:
        service.database.close()


@retention_app.command("status")
def retention_status(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.retention_status()))
    finally:
        service.database.close()


@retention_app.command("report")
def retention_report(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.retention_report()))
    finally:
        service.database.close()


@retention_app.command("plan")
def retention_plan(policy_id: str = typer.Option("preserve-all"), config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(service.plan_retention(policy_id).model_dump_json())
    finally:
        service.database.close()


@retention_app.command("apply")
def retention_apply(
    plan_id: str,
    approved_hash: str,
    confirm: bool = typer.Option(False, help="Confirm the approved retention plan"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _trust_service(config)
    try:
        console.print_json(service.apply_retention(plan_id, approved_hash, confirm=confirm).model_dump_json())
    finally:
        service.database.close()


@review_packages_app.command("create")
def review_packages_create(action_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(service.create_review_package(action_id).model_dump_json())
    finally:
        service.database.close()


@review_packages_app.command("verify")
def review_packages_verify(package_path: Path, config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.verify_review_package(package_path)))
    finally:
        service.database.close()


@review_packages_app.command("inspect")
def review_packages_inspect(package_path: Path, config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.verify_review_package(package_path)))
    finally:
        service.database.close()


@provenance_app.command("list")
def provenance_list(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.list_provenance_manifests()))
    finally:
        service.database.close()


@provenance_app.command("show")
def provenance_show(manifest_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.get_provenance_manifest(manifest_id)))
    finally:
        service.database.close()


@provenance_app.command("create")
def provenance_create(
    subject_kind: str,
    subject_id: str,
    subject_version: int = typer.Option(1),
    payload_json: str = typer.Option("{}", help="Canonical JSON payload for the provenance record"),
    config: Path | None = typer.Option(None),
) -> None:
    service = _trust_service(config)
    try:
        payload = json.loads(payload_json)
        request = ProvenanceCreateRequest(
            subject_kind=subject_kind,
            subject_id=subject_id,
            subject_version=subject_version,
            payload=payload if isinstance(payload, dict) else {"value": payload},
        )
        console.print_json(json.dumps(service.create_provenance_manifest(request)))
    finally:
        service.database.close()


@provenance_app.command("verify")
def provenance_verify(manifest_id: str, config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.verify_provenance_manifest(manifest_id)))
    finally:
        service.database.close()


@signing_app.command("list")
def signing_list(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.list_signing_keys()))
    finally:
        service.database.close()


@signing_app.command("create")
def signing_create(key_name: str, activate: bool = typer.Option(True), config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.create_signing_key(key_name, activate=activate)))
    finally:
        service.database.close()


@signing_app.command("rotate")
def signing_rotate(key_id: str, next_key_name: str | None = typer.Option(None), config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.rotate_signing_key(key_id, next_key_name=next_key_name)))
    finally:
        service.database.close()


@signing_app.command("revoke")
def signing_revoke(key_id: str, reason: str = typer.Option("revoked"), config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.revoke_signing_key(key_id, reason=reason)))
    finally:
        service.database.close()


@trust_alerts_app.command("list")
def trust_alerts_list(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.list_trust_alerts()))
    finally:
        service.database.close()


@trust_alerts_app.command("refresh")
def trust_alerts_refresh(config: Path | None = typer.Option(None)) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.refresh_trust_alerts()))
    finally:
        service.database.close()


@trust_alerts_app.command("acknowledge")
def trust_alerts_acknowledge(
    alert_id: str,
    reviewer: str = typer.Option("manual"),
    reason: str = typer.Option(""),
    config: Path | None = typer.Option(None),
) -> None:
    service = _trust_service(config)
    try:
        console.print_json(json.dumps(service.acknowledge_trust_alert(alert_id, reviewer=reviewer, reason=reason)))
    finally:
        service.database.close()
