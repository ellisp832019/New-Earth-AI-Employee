from fastapi.testclient import TestClient

from gaia.api import create_app


def test_programme_workspace_route_returns_canonical_payload(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/integration/v1/project-officer/programme/workspace")

        assert response.status_code == 200
        payload = response.json()
        assert payload["selected_project_id"] == "sample"
        assert "summary" in payload
        assert "architecture_registry" in payload
        assert "dependency_graph" in payload
        assert "impact_analysis" in payload
        assert "roadmap" in payload
        assert "release_trains" in payload
        assert "programme_packages" in payload
