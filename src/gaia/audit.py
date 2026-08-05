from __future__ import annotations

import json
from typing import Any

from gaia.models import AuditEvent


class AuditRecorder:
    def __init__(self, database: Database) -> None:
        self.database = database

    def record(
        self,
        *,
        category: str,
        operation: str,
        outcome: str,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        error_classification: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            category=category,
            operation=operation,
            outcome=outcome,  # type: ignore[arg-type]
            project_id=project_id,
            metadata=metadata or {},
            error_classification=error_classification,
        )
        self.database.insert_audit_event(event)
        return event

    @staticmethod
    def safe_metadata(metadata: dict[str, Any]) -> str:
        return json.dumps(metadata, sort_keys=True, default=str)


from gaia.db import Database  # noqa: E402
