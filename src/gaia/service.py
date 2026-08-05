from __future__ import annotations

from collections import Counter

from gaia.audit import AuditRecorder
from gaia.config import Settings
from gaia.db import Database
from gaia.git_inspector import GitInspector
from gaia.models import ProjectConfig, RepositorySnapshot, SearchResult
from gaia.reports import foundation_report_json, foundation_report_markdown
from gaia.scanner import DocumentScanner


class ProjectService:
    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.audit = AuditRecorder(self.database)
        self.git = GitInspector(settings.git_timeout_seconds, settings.max_git_output_bytes)
        self.scanner = DocumentScanner(settings.max_file_bytes)

    def get_project(self, project_id: str) -> ProjectConfig:
        try:
            return self.settings.projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def scan(self, project_id: str) -> list[dict[str, object]]:
        project = self.get_project(project_id)
        before = self.git.inspect(project.root)
        tracked = self.git.tracked_files(project.root)
        try:
            records = self.scanner.scan(project, tracked)
            after = self.git.inspect(project.root)
            if before.model_dump() != after.model_dump():
                self.audit.record(
                    category="safety",
                    operation="read_only_integrity_check",
                    project_id=project_id,
                    outcome="failure",
                    metadata={"message": "Repository state changed during scan"},
                    error_classification="RepositoryStateChanged",
                )
                raise RuntimeError("Repository state changed during read-only scan")
            self.database.replace_documents(project_id, records)
            self.audit.record(
                category="documents",
                operation="scan",
                project_id=project_id,
                outcome="success",
                metadata={"document_count": len(records)},
            )
            return [record.model_dump(mode="json", exclude={"content"}) for record in records]
        except Exception as exc:
            self.audit.record(
                category="documents",
                operation="scan",
                project_id=project_id,
                outcome="failure",
                metadata={"error": str(exc)},
                error_classification=type(exc).__name__,
            )
            raise

    def snapshot(self, project_id: str) -> RepositorySnapshot:
        project = self.get_project(project_id)
        git_state = self.git.inspect(project.root)
        rows = self.database.list_documents(project_id)
        counts = Counter(str(row["extension"]) for row in rows)
        statuses = Counter(str(row["indexing_status"]) for row in rows)
        warnings = [str(row["warning"]) for row in rows if row.get("warning")]
        important_paths = {
            important: (project.root / important).exists() for important in project.important_paths
        }
        snapshot = RepositorySnapshot(
            project_id=project_id,
            project_name=project.name,
            project_root=str(project.root),
            git=git_state,
            document_count=len(rows),
            indexed_count=statuses.get("indexed", 0),
            skipped_count=statuses.get("skipped", 0),
            failed_count=statuses.get("failed", 0),
            counts_by_extension=dict(counts),
            scan_warnings=warnings[:100],
            important_paths=important_paths,
        )
        self.database.insert_snapshot(snapshot)
        self.audit.record(
            category="repository",
            operation="snapshot",
            project_id=project_id,
            outcome="success",
            metadata={"snapshot_id": snapshot.snapshot_id},
        )
        return snapshot

    def search(
        self,
        project_id: str,
        query: str,
        limit: int = 20,
        path_prefix: str | None = None,
        extension: str | None = None,
    ) -> list[SearchResult]:
        self.get_project(project_id)
        results = self.database.search(
            project_id, query, limit=limit, path_prefix=path_prefix, extension=extension
        )
        self.audit.record(
            category="documents",
            operation="search",
            project_id=project_id,
            outcome="success",
            metadata={"query_length": len(query), "result_count": len(results)},
        )
        return results

    def foundation_report(self, project_id: str, format_name: str = "markdown") -> str:
        snapshot = self.database.latest_snapshot(project_id) or self.snapshot(project_id)
        self.audit.record(
            category="reports",
            operation="foundation_report",
            project_id=project_id,
            outcome="success",
            metadata={"snapshot_id": snapshot.snapshot_id, "format": format_name},
        )
        return foundation_report_json(snapshot) if format_name == "json" else foundation_report_markdown(snapshot)
