from fastapi.testclient import TestClient

from gaia.api import create_app


def test_project_officer_workspace_routes(settings):
    with TestClient(create_app(settings)) as client:
        health = client.post("/projects/sample/health")
        assert health.status_code == 200
        assert health.json()["project_id"] == "sample"

        assert client.get("/portfolio/health").status_code == 200
        assert client.get("/portfolio/changes").status_code == 200
        assert client.get("/portfolio/recommendations").status_code == 200

        generated = client.post("/projects/sample/recommendations/generate")
        assert generated.status_code == 200
        recommendations = generated.json()
        assert recommendations

        queue = client.get("/recommendations/queue", params={"project_id": "sample"})
        assert queue.status_code == 200
        active = next(item for item in queue.json() if item["lifecycle_state"] == "active")

        package = client.post(f"/recommendations/{active['recommendation_id']}/work-packages")
        assert package.status_code == 200
        work_package = package.json()
        work_package_id = work_package["work_package_id"]

        assert client.get(f"/work-packages/{work_package_id}").status_code == 200
        assert client.get(f"/work-packages/{work_package_id}/summary").status_code == 200
        assert client.get(f"/work-packages/{work_package_id}/prompt").status_code == 200
        assert client.get(f"/work-packages/{work_package_id}/revisions").status_code == 200
        assert client.get(f"/work-packages/{work_package_id}/approval-decisions").status_code == 200
        assert client.get(f"/work-packages/{work_package_id}/handoffs").status_code == 200
        assert client.get(f"/work-packages/{work_package_id}/outcomes").status_code == 200
        assert client.get("/projects/sample/changes/findings").status_code == 200

        assert client.post(f"/work-packages/{work_package_id}/submit-for-review", params={"revision_number": 1}).status_code == 200
        assert client.post(
            f"/work-packages/{work_package_id}/approve",
            params={"revision_number": 1, "human_note": "Approved in test"},
        ).status_code == 200
        assert client.post(f"/work-packages/{work_package_id}/handoff", params={"revision_number": 1}).status_code == 200
