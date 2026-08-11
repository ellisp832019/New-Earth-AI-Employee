from fastapi.testclient import TestClient

from gaia.api import create_app
from tests.governance_helpers import FakeGovernanceContextService, sample_governance_context


def test_health(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_projects(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/projects")
        assert response.status_code == 200
        assert response.json()[0]["project_id"] == "sample"
        assert "health_rules" not in response.json()[0]
        assert "metadata" not in response.json()[0]


def test_scan_search_report(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post("/projects/sample/scan").status_code == 200
        assert client.get("/projects/sample/search", params={"q": "MicroGrow"}).json()
        assert client.get("/projects/sample/documents").status_code == 200
        assert client.get("/projects/sample/snapshots").status_code == 200
        response = client.post("/projects/sample/reports/foundation")
        assert response.status_code == 200
        assert "GAIA Foundation Report" in response.text
        assert client.get("/projects/sample/snapshots/latest").status_code == 200
        assert client.get("/audit/events").status_code == 200
        assert client.get("/models/status").status_code == 200
        assert client.get("/models").status_code == 200
        assert client.get("/integration/v1/capabilities").status_code == 200
        assert client.get("/signing/keys").status_code == 200
        assert client.get("/trust/alerts").status_code == 200
        assert client.get("/retention/report").status_code == 200


def test_agent_ask_api(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/agent/ask",
            json={"project_id": "sample", "question": "What was completed most recently?", "deterministic_only": True},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["project_id"] == "sample"
        assert payload["run_id"]
        assert client.get("/agent/runs").status_code == 200
        assert client.get(f"/agent/runs/{payload['run_id']}").status_code == 200


def test_unknown_project(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/projects/missing").status_code == 404


def test_governance_api_endpoints(settings):
    app = create_app(settings)
    app.state.service.governance_context_service = FakeGovernanceContextService(sample_governance_context())
    with TestClient(app) as client:
        response = client.get("/governance")
        assert response.status_code == 200
        assert response.json()["source"]["snapshot_id"] == "snapshot-001"

        assert client.get("/governance/status").status_code == 200
        assert client.get("/governance/findings").status_code == 200
        assert client.get("/governance/project/sample").status_code == 200
        assert client.get("/governance/snapshot").status_code == 200
        brief = client.get("/governance/brief")
        assert brief.status_code == 200
        assert "Architecture Governance" in brief.json()["markdown"]


def test_public_programme_api_surfaces_and_schema_excludes_internal_workspace(settings):
    with TestClient(create_app(settings)) as client:
        summary = client.get("/integration/v1/programme/summary")
        assert summary.status_code == 200
        payload = summary.json()
        assert payload["selected_project_id"] == "sample"
        assert "summary" in payload
        assert payload["summary"]["trust_alert_count"] >= 0
        assert payload["summary"]["provenance_manifest_count"] >= 0
        assert "stale_evidence_projects" in payload["summary"]

        assert client.get("/integration/v1/programme/overview").status_code == 200
        assert client.get("/integration/v1/architecture/entities").status_code == 200
        assert client.get("/integration/v1/architecture/relationships").status_code == 200
        assert client.get("/integration/v1/dependencies/graph").status_code == 200
        assert client.get("/integration/v1/dependencies/findings").status_code == 200
        assert client.get("/integration/v1/change-impact/summary").status_code == 200
        assert client.get("/integration/v1/change-impact/recommendations").status_code == 200
        assert client.get("/integration/v1/release-trains").status_code == 200
        assert client.get("/integration/v1/programme-packages").status_code == 200

        openapi = client.get("/openapi.json").json()
        assert "/integration/v1/project-officer/programme/workspace" not in openapi["paths"]
