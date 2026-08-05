from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from gaia.conversation import AgentRunRecord
from gaia.models import AuditEvent, DocumentRecord, RepositorySnapshot, SearchResult


class Database:
    SCHEMA_VERSION = 5

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
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                question TEXT NOT NULL,
                question_category TEXT NOT NULL,
                snapshot_id TEXT,
                retrieval_queries_json TEXT NOT NULL,
                selected_evidence_json TEXT NOT NULL,
                provider TEXT NOT NULL,
                model_name TEXT,
                start_timestamp TEXT NOT NULL,
                finish_timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                structured_answer_json TEXT NOT NULL,
                confidence TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                prompt_injection_warnings_json TEXT NOT NULL,
                safe_error TEXT,
                usage_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                category TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_identifier TEXT,
                source_agent_run_id TEXT,
                evidence_references_json TEXT NOT NULL,
                dependency_task_ids_json TEXT NOT NULL,
                blocker_description TEXT,
                assigned_to TEXT,
                due_date TEXT,
                completion_criteria TEXT NOT NULL,
                completion_evidence_json TEXT NOT NULL,
                approval_requirement INTEGER NOT NULL,
                tags_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version INTEGER NOT NULL,
                manual_override_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS task_history (
                history_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS drafts (
                draft_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                draft_type TEXT NOT NULL,
                project_id TEXT NOT NULL,
                source_task_id TEXT,
                source_agent_run_id TEXT,
                current_revision INTEGER NOT NULL,
                current_content_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_references_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                approval_requirement INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS draft_revisions (
                revision_id TEXT PRIMARY KEY,
                draft_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                author TEXT NOT NULL,
                change_reason TEXT NOT NULL,
                UNIQUE(draft_id, revision_number)
            );
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                request_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                project_id TEXT NOT NULL,
                source_task_id TEXT,
                source_draft_id TEXT,
                requesting_source TEXT NOT NULL,
                proposed_action TEXT NOT NULL,
                exact_target_description TEXT NOT NULL,
                write_boundary TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                preview_summary TEXT NOT NULL,
                approved_content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expiry_timestamp TEXT,
                status TEXT NOT NULL,
                reviewer TEXT,
                decision_timestamp TEXT,
                decision_reason TEXT,
                audit_references_json TEXT NOT NULL,
                invalidation_reason TEXT,
                version INTEGER NOT NULL,
                action_id TEXT,
                action_type TEXT,
                manifest_id TEXT,
                manifest_version INTEGER,
                canonical_target TEXT,
                previous_content_hash TEXT,
                proposed_content_hash TEXT,
                approval_binding_hash TEXT,
                approval_scope TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_briefs (
                brief_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                repository_snapshot_json TEXT NOT NULL,
                verified_facts_json TEXT NOT NULL,
                inferences_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                unknowns_json TEXT NOT NULL,
                markdown TEXT NOT NULL,
                source_task_ids_json TEXT NOT NULL,
                source_approval_ids_json TEXT NOT NULL,
                source_run_ids_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS permission_manifests (
                manifest_id TEXT PRIMARY KEY,
                manifest_version INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                allowed_action_types_json TEXT NOT NULL,
                allowed_target_roots_json TEXT NOT NULL,
                allowed_file_extensions_json TEXT NOT NULL,
                denied_path_patterns_json TEXT NOT NULL,
                maximum_file_size INTEGER NOT NULL,
                overwrite_policy TEXT NOT NULL,
                backup_requirement INTEGER NOT NULL,
                rollback_requirement INTEGER NOT NULL,
                approval_requirement INTEGER NOT NULL,
                risk_ceiling TEXT NOT NULL,
                expiry_timestamp TEXT,
                creation_source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                review_notes TEXT
            );
            CREATE TABLE IF NOT EXISTS output_actions (
                action_id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                title TEXT NOT NULL,
                project_id TEXT NOT NULL,
                source_task_id TEXT,
                source_draft_id TEXT,
                source_draft_revision INTEGER,
                source_approval_id TEXT,
                manifest_id TEXT NOT NULL,
                manifest_version INTEGER NOT NULL,
                canonical_target TEXT NOT NULL,
                proposed_content TEXT NOT NULL,
                previous_content_hash TEXT,
                proposed_content_hash TEXT NOT NULL,
                preview TEXT NOT NULL,
                diff TEXT NOT NULL,
                risk TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expiry_timestamp TEXT,
                execution_time TEXT,
                execution_receipt_id TEXT,
                approval_id TEXT,
                approval_binding_hash TEXT,
                approval_status TEXT,
                approval_decision_timestamp TEXT,
                approval_reviewer TEXT,
                approval_reason TEXT,
                denial_reason TEXT,
                backup_path TEXT,
                rollback_available INTEGER NOT NULL,
                operator TEXT,
                warnings_json TEXT NOT NULL,
                result TEXT
            );
            CREATE TABLE IF NOT EXISTS action_previews (
                preview_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                preview TEXT NOT NULL,
                diff TEXT NOT NULL,
                previous_content_hash TEXT,
                proposed_content_hash TEXT NOT NULL,
                target_path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS execution_receipts (
                receipt_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                approval_id TEXT,
                manifest_id TEXT NOT NULL,
                manifest_version INTEGER NOT NULL,
                source_draft_id TEXT,
                source_draft_revision INTEGER,
                target_path TEXT NOT NULL,
                previous_hash TEXT,
                resulting_hash TEXT NOT NULL,
                backup_path TEXT,
                timestamp TEXT NOT NULL,
                operator TEXT NOT NULL,
                result TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                rollback_available INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS output_backups (
                backup_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                target_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                verified INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rollback_records (
                rollback_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                receipt_id TEXT,
                target_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                previous_hash TEXT,
                resulting_hash TEXT,
                created_at TEXT NOT NULL,
                executed_at TEXT,
                status TEXT NOT NULL,
                reason TEXT
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
        self._ensure_columns(
            "approvals",
            {
                "action_id": "TEXT",
                "action_type": "TEXT",
                "manifest_id": "TEXT",
                "manifest_version": "INTEGER",
                "canonical_target": "TEXT",
                "previous_content_hash": "TEXT",
                "proposed_content_hash": "TEXT",
                "approval_binding_hash": "TEXT",
                "approval_scope": "TEXT",
            },
        )
        self.connection.commit()
        self.connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
        self.connection.commit()

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        existing = {
            str(row["name"])
            for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, type_name in columns.items():
            if name not in existing:
                self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {type_name}")

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

    def insert_agent_run(self, run: AgentRunRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO agent_runs(
                    run_id, project_id, question, question_category, snapshot_id,
                    retrieval_queries_json, selected_evidence_json, provider, model_name,
                    start_timestamp, finish_timestamp, status, structured_answer_json,
                    confidence, warnings_json, prompt_injection_warnings_json, safe_error, usage_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.project_id,
                    run.question,
                    run.question_category,
                    run.snapshot_id,
                    json.dumps(run.retrieval_queries, default=str, sort_keys=True),
                    json.dumps([item.model_dump(mode="json") for item in run.selected_evidence], default=str, sort_keys=True),
                    run.provider,
                    run.model_name,
                    run.start_timestamp.isoformat(),
                    run.finish_timestamp.isoformat(),
                    run.status,
                    json.dumps(run.structured_answer, default=str, sort_keys=True),
                    run.confidence,
                    json.dumps(run.warnings, default=str, sort_keys=True),
                    json.dumps(run.prompt_injection_warnings, default=str, sort_keys=True),
                    run.safe_error,
                    json.dumps(run.usage, default=str, sort_keys=True),
                ),
            )

    def list_agent_runs(self, limit: int = 100) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT * FROM agent_runs ORDER BY start_timestamp DESC LIMIT ?", (max(1, min(limit, 1000)),)
        ).fetchall()
        return [self._row_to_agent_run_dict(row) for row in rows]

    def get_agent_run(self, run_id: str) -> dict[str, object] | None:
        row = self.connection.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row_to_agent_run_dict(row) if row else None

    def _row_to_agent_run_dict(self, row: sqlite3.Row) -> dict[str, object]:
        item = dict(row)
        item["retrieval_queries"] = json.loads(str(item.pop("retrieval_queries_json")))
        item["selected_evidence"] = json.loads(str(item.pop("selected_evidence_json")))
        item["structured_answer"] = json.loads(str(item.pop("structured_answer_json")))
        item["warnings"] = json.loads(str(item.pop("warnings_json")))
        item["prompt_injection_warnings"] = json.loads(str(item.pop("prompt_injection_warnings_json")))
        item["usage"] = json.loads(str(item.pop("usage_json")))
        return item


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
