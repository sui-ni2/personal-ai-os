from fastapi.testclient import TestClient


def test_project_control_center_uses_authoritative_project_state(client: TestClient) -> None:
    created = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "task",
            "key": "verify-control-center",
            "value": {"summary": "Verify the project control center"},
            "source": "test",
        },
    )
    assert created.status_code == 200
    response = client.get("/api/projects/general/control-center")
    assert response.status_code == 200
    body = response.json()
    assert body["state"]["tasks"][0]["value"]["summary"] == "Verify the project control center"
    assert body["continuity"]["provider_session_copied"] is False
    assert body["recovery"]["status"] == "clean"
