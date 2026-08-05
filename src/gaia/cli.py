from __future__ import annotations

import shutil
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from gaia import __version__
from gaia.api import create_app
from gaia.config import load_settings
from gaia.db import Database
from gaia.reports import write_report
from gaia.service import ProjectService

app = typer.Typer(help="GAIA local-first project-control employee")
project_app = typer.Typer(help="Inspect registered projects")
projects_app = typer.Typer(help="List registered projects")
app.add_typer(project_app, name="project")
app.add_typer(projects_app, name="projects")
console = Console()


def _service(config: Path | None = None) -> ProjectService:
    settings = load_settings(config)
    return ProjectService(settings, Database(settings.database_path))


@app.command()
def doctor(config: Path | None = typer.Option(None, help="Path to project configuration")) -> None:
    """Check configuration, database, Git and registered project roots."""
    settings = load_settings(config)
    database = Database(settings.database_path)
    rows = []
    rows.append(("GAIA version", __version__, True))
    rows.append(("Configuration", str(settings.config_path), settings.config_path.exists()))
    rows.append(("Database", str(settings.database_path), True))
    rows.append(("SQLite FTS5", str(database.fts5_available), True))
    rows.append(("Git executable", shutil.which("git") or "not found", shutil.which("git") is not None))
    for project in settings.projects.values():
        rows.append((f"Project {project.project_id}", str(project.root), project.root.exists()))
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


@app.command()
def serve(
    host: str | None = typer.Option(None),
    port: int | None = typer.Option(None),
    config: Path | None = typer.Option(None),
) -> None:
    """Start the local FastAPI service."""
    settings = load_settings(config)
    uvicorn.run(create_app(settings), host=host or settings.api_host, port=port or settings.api_port)
