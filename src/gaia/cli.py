from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from gaia import __version__
from gaia.agent import AgentService
from gaia.api import create_app
from gaia.config import load_settings
from gaia.db import Database
from gaia.providers import ProviderRegistry
from gaia.reports import write_report
from gaia.service import ProjectService

app = typer.Typer(help="GAIA local-first project-control employee")
project_app = typer.Typer(help="Inspect registered projects")
projects_app = typer.Typer(help="List registered projects")
models_app = typer.Typer(help="Model provider status")
agent_app = typer.Typer(help="Conversational agent commands")
agent_runs_app = typer.Typer(help="Agent run history")
app.add_typer(project_app, name="project")
app.add_typer(projects_app, name="projects")
app.add_typer(models_app, name="models")
app.add_typer(agent_app, name="agent")
agent_app.add_typer(agent_runs_app, name="runs")
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
def agent_runs_list(config: Path | None = typer.Option(None)) -> None:
    _service, database, _registry, _agent = _bundle(config)
    try:
        console.print_json(json.dumps(database.list_agent_runs()))
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
