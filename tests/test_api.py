from fastapi.testclient import TestClient

from gaia.api import create_app


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
