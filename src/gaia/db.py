from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from gaia.models import AuditEvent, DocumentRecord, RepositorySnapshot, SearchResult


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.fts5_available = False
        self.initialise()

    def close(self) -> None:
        self.connection.close()

    def initialise(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS documents (
                project_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                extension TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_utc TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                tracked INTEGER,
                indexing_status TEXT NOT NULL,
                warning TEXT,
                scanned_at TEXT NOT NULL,
                content TEXT,
                PRIMARY KEY(project_id, relative_path)
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                operation TEXT NOT NULL,
                project_id TEXT,
                outcome TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                error_classification TEXT
            );
            """
        )
        try:
            self.connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(project_id, relative_path, content)"
            )
            self.fts5_available = True
        except sqlite3.OperationalError:
            self.fts5_available = False
        self.connection.commit()

    def replace_documents(self, project_id: str, records: Iterable[DocumentRecord]) -> None:
        records = list(records)
        with self.connection:
            self.connection.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))
            if self.fts5_available:
                self.connection.execute("DELETE FROM documents_fts WHERE project_id = ?", (project_id,))
            for record in records:
                self.connection.execute(
                    """
                    INSERT INTO documents (
                        project_id, relative_path, extension, size_bytes, modified_utc,
                        sha256, tracked, indexing_status, warning, scanned_at, content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.project_id,
                        record.relative_path,
                        record.extension,
                        record.size_bytes,
                        record.modified_utc.isoformat(),
                        record.sha256,
                        None if record.tracked is None else int(record.tracked),
                        record.indexing_status,
                        record.warning,
                        record.scanned_at.isoformat(),
                        record.content,
                    ),
                )
                if self.fts5_available and record.content and record.indexing_status == "indexed":
                    self.connection.execute(
                        "INSERT INTO documents_fts(project_id, relative_path, content) VALUES (?, ?, ?)",
                        (record.project_id, record.relative_path, record.content),
                    )

    def list_documents(self, project_id: str) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT * FROM documents WHERE project_id = ? ORDER BY relative_path", (project_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def search(
        self,
        project_id: str,
        query: str,
        *,
        limit: int = 20,
        path_prefix: str | None = None,
        extension: str | None = None,
    ) -> list[SearchResult]:
        limit = max(1, min(limit, 100))
        if self.fts5_available:
            sql = (
                "SELECT relative_path, snippet(documents_fts, 2, '[', ']', ' ... ', 18) AS snippet, "
                "bm25(documents_fts) AS score FROM documents_fts "
                "WHERE project_id = ? AND documents_fts MATCH ?"
            )
            params: list[object] = [project_id, query]
            if path_prefix:
                sql += " AND relative_path LIKE ? ESCAPE '\\'"
                params.append(f"{_escape_like(path_prefix)}%")
            sql += " ORDER BY score LIMIT ?"
            params.append(limit)
            try:
                rows = self.connection.execute(sql, params).fetchall()
                results = []
                for row in rows:
                    ext = Path(row["relative_path"]).suffix.lower()
                    if extension and ext != extension.lower():
                        continue
                    results.append(
                        SearchResult(
                            relative_path=row["relative_path"],
                            extension=ext,
                            snippet=row["snippet"] or "",
                            score=float(row["score"]),
                        )
                    )
                return results[:limit]
            except sqlite3.OperationalError:
                pass

        sql = (
            "SELECT relative_path, extension, content FROM documents "
            "WHERE project_id = ? AND content LIKE ? ESCAPE '\\'"
        )
        params = [project_id, f"%{_escape_like(query)}%"]
        if path_prefix:
            sql += " AND relative_path LIKE ? ESCAPE '\\'"
            params.append(f"{_escape_like(path_prefix)}%")
        if extension:
            sql += " AND extension = ?"
            params.append(extension.lower())
        sql += " ORDER BY relative_path LIMIT ?"
        params.append(limit)
        rows = self.connection.execute(sql, params).fetchall()
        return [
            SearchResult(
                relative_path=row["relative_path"],
                extension=row["extension"],
                snippet=_make_snippet(row["content"] or "", query),
            )
            for row in rows
        ]

    def insert_snapshot(self, snapshot: RepositorySnapshot) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO snapshots(snapshot_id, project_id, created_at, payload_json) VALUES (?, ?, ?, ?)",
                (
                    snapshot.snapshot_id,
                    snapshot.project_id,
                    snapshot.created_at.isoformat(),
                    snapshot.model_dump_json(),
                ),
            )

    def list_snapshots(self, project_id: str) -> list[RepositorySnapshot]:
        rows = self.connection.execute(
            "SELECT payload_json FROM snapshots WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return [RepositorySnapshot.model_validate_json(row["payload_json"]) for row in rows]

    def latest_snapshot(self, project_id: str) -> RepositorySnapshot | None:
        row = self.connection.execute(
            "SELECT payload_json FROM snapshots WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return RepositorySnapshot.model_validate_json(row["payload_json"]) if row else None

    def insert_audit_event(self, event: AuditEvent) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO audit_events(
                    event_id, timestamp, category, operation, project_id,
                    outcome, metadata_json, error_classification
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.category,
                    event.operation,
                    event.project_id,
                    event.outcome,
                    json.dumps(event.metadata, default=str, sort_keys=True),
                    event.error_classification,
                ),
            )

    def list_audit_events(self, limit: int = 100) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?", (max(1, min(limit, 1000)),)
        ).fetchall()
        events = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(str(item.pop("metadata_json")))
            events.append(item)
        return events


def _make_snippet(content: str, query: str, radius: int = 120) -> str:
    lower = content.lower()
    index = lower.find(query.lower())
    if index < 0:
        return content[: radius * 2].replace("\n", " ")
    start = max(0, index - radius)
    end = min(len(content), index + len(query) + radius)
    return content[start:end].replace("\n", " ")


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
