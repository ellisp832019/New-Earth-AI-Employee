from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from gaia.db import Database
from gaia.governance_context import GovernanceCacheRecord, NeosGovernanceClient
from gaia.service import ProjectService
from tests.governance_helpers import (
    FakeGovernanceContextService,
    governance_transport,
    sample_governance_context,
)


def test_governance_context_service_builds_context_and_caches(settings):
    database = Database(settings.database_path)
    service = ProjectService(settings, database)
    service.governance_context_service.client = NeosGovernanceClient(transport=governance_transport())
    try:
        context = service.governance_context("sample")
        assert context.source.available is True
        assert context.source.snapshot is not None
        assert context.source.snapshot.snapshot_id == "snapshot-001"
        assert context.findings[0].source.rule_id == "NEOS-GOV-001"
        assert context.priority.operational_priority == "P0"
        assert context.work_package is not None
        assert context.work_package.rule_id == "NEOS-GOV-001"
        assert context.brief is not None
        assert "Architecture Governance" in context.brief.markdown
        assert "NEOS-GOV-001" in context.brief.markdown
        cached = database.latest_governance_snapshot()
        assert cached is not None
        assert cached.project_id == "sample"
        assert cached.snapshot_id == "snapshot-001"
        assert context.source.cache_state == "none"
        again = service.governance_context("sample")
        assert again.source.cache_state == "fresh"
    finally:
        service.close()


def test_governance_client_degrades_on_version_mismatch(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        payload = {
            "schema_version": 1,
            "governance_version": "2.0.0",
            "neos_version": "2.0.0",
            "status": "READY",
            "summary": {"readiness": "READY"},
            "platform_core": {"status": "AVAILABLE"},
            "observed": {"estate": "sample"},
            "declared": {"estate": "sample"},
        }
        if path == "/governance":
            return httpx.Response(200, json={**payload, "findings": [], "systems": [], "snapshot": None})
        if path == "/governance/status":
            return httpx.Response(200, json={**payload, "snapshot": None})
        if path == "/governance/findings":
            return httpx.Response(200, json={"findings": []})
        if path == "/governance/snapshot":
            return httpx.Response(200, json={"schema_version": 1, "snapshot_id": "snapshot-001", "readiness": "READY"})
        return httpx.Response(404, json={"error": "not found"})

    database = Database(settings.database_path)
    service = ProjectService(settings, database)
    service.governance_context_service.client = NeosGovernanceClient(transport=httpx.MockTransport(handler))
    try:
        context = service.governance_context("sample")
        assert context.source.available is False
        assert context.source.compatibility_state in {"unavailable", "cached"}
        assert context.brief is not None
        assert context.brief.estate_status == "UNKNOWN"
    finally:
        service.close()


def test_governance_context_preserves_source_and_interpretation_separation(settings):
    database = Database(settings.database_path)
    service = ProjectService(settings, database)
    service.governance_context_service.client = NeosGovernanceClient(transport=governance_transport())
    try:
        context = service.governance_context("sample")
        source = context.findings[0].source
        assert source.finding_id == "finding-001"
        assert source.rule_id == "NEOS-GOV-001"
        assert source.severity == "ERROR"
        assert source.canonical_owner == "Platform Core"
        assert source.declared_state == {"identity": "canonical"}
        assert source.observed_state == {"identity": "observed"}
        assert source.snapshot_id == "snapshot-001"
        assert source.evidence == {"source": ["governance/status"]}
        assert source.governance_version == "1.0.0"
        assert source.neos_version == "1.0.0"
        assert context.priority.operational_priority != source.severity
        assert context.work_package is not None
        assert context.work_package.auto_execute is False
        assert context.interpretation.explanation != source.explanation
    finally:
        service.close()


def test_governance_context_handles_unavailable_timeout_malformed_and_cache_states(settings):
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    def malformed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"content-type": "application/json"})

    timeout_service = ProjectService(settings, Database(settings.database_path))
    timeout_service.governance_context_service.client = NeosGovernanceClient(transport=httpx.MockTransport(timeout_handler))
    try:
        context = timeout_service.governance_context("sample")
        assert context.source.available is False
        assert context.source.compatibility_state == "unavailable"
        assert context.source.cache_state == "none"
        assert context.source.snapshot is not None
        assert context.source.snapshot.readiness == "UNKNOWN"
    finally:
        timeout_service.close()

    malformed_service = ProjectService(settings, Database(settings.database_path))
    malformed_service.governance_context_service.client = NeosGovernanceClient(transport=httpx.MockTransport(malformed_handler))
    try:
        context = malformed_service.governance_context("sample")
        assert context.source.available is False
        assert context.source.compatibility_state == "unavailable"
        assert context.source.snapshot is not None
        assert context.source.snapshot.readiness == "UNKNOWN"
    finally:
        malformed_service.close()

    stale_database = Database(settings.database_path)
    stale_service = ProjectService(settings, stale_database)
    stale_service.governance_context_service.client = NeosGovernanceClient(transport=httpx.MockTransport(timeout_handler))
    try:
        stale_database.insert_governance_snapshot(
            GovernanceCacheRecord(
                source_url=stale_service.governance_context_service.client.base_url,
                project_id="sample",
                finding_id="finding-001",
                received_at=datetime.now(UTC) - timedelta(days=2),
                source_timestamp=datetime.now(UTC) - timedelta(days=2),
                governance_version="1.0.0",
                neos_version="1.0.0",
                snapshot_id="snapshot-old",
                source_hash="stale-hash",
                compatibility_state="cached",
                payload_json=sample_governance_context().source.model_dump(mode="json"),
            )
        )
        context = stale_service.governance_context("sample")
        assert context.source.cache_state == "stale"
        assert context.source.compatibility_state == "cached"
        assert context.freshness.state == "unknown"
        assert context.source.snapshot is not None
    finally:
        stale_service.close()


@pytest.mark.parametrize("estate_status", ["READY", "READY_WITH_WARNINGS", "NOT_READY", "UNKNOWN"])
def test_governance_status_labels_are_preserved(settings, estate_status: str):
    database = Database(settings.database_path)
    service = ProjectService(settings, database)
    context_value = sample_governance_context()
    context_value.source.status.status = estate_status
    context_value.source.status.summary["readiness"] = estate_status
    context_value.source.report.summary["readiness"] = estate_status
    context_value.brief.estate_status = estate_status
    service.governance_context_service = FakeGovernanceContextService(context_value)
    try:
        context = service.governance_context("sample")
        assert context.source.status is not None
        assert context.source.status.status == estate_status
        assert context.brief is not None
        assert context.brief.estate_status == estate_status
    finally:
        service.close()
