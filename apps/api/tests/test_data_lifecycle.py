from __future__ import annotations

import json

from fastapi.testclient import TestClient
from personal_ai_os_core import MessageRole


def test_core_data_export_is_scoped_and_credential_free(client: TestClient, runtime) -> None:
    created_project = client.post(
        "/api/projects",
        json={"name": "Export fixture", "description": "A user-owned project for export coverage."},
    )
    assert created_project.status_code == 201
    project_id = created_project.json()["id"]
    conversation = runtime.database.create_conversation(
        provider="openai", model="openai-test", project_id=project_id, title="Export fixture"
    )
    runtime.database.add_message(conversation.id, MessageRole.USER, "Portable conversation content")
    created_memory = client.post(
        "/api/memory",
        json={
            "type": "fact",
            "text": "Portable memory content",
            "source": "test",
            "confidence": 1,
            "project_id": project_id,
        },
    )
    assert created_memory.status_code == 201
    runtime.database.set_setting("internal_settings_marker", "not-exported")

    response = client.get("/api/data/core-export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "personal-ai-os-core-data-export-v1"
    assert payload["credentials_included"] is False
    assert payload["data"]["conversations"][0]["id"] == conversation.id
    assert payload["data"]["messages"][0]["content"] == "Portable conversation content"
    assert payload["data"]["memories"][0]["text"] == "Portable memory content"
    assert "internal_settings_marker" not in str(payload)
    assert "connector endpoints" in " ".join(payload["excluded_scopes"])


def test_core_data_erase_requires_acknowledgement_and_preserves_static_projects(
    client: TestClient, runtime
) -> None:
    created_project = client.post(
        "/api/projects",
        json={"name": "Erase fixture", "description": "A user-owned project for erase coverage."},
    )
    assert created_project.status_code == 201
    project_id = created_project.json()["id"]
    runtime.database.create_memory(
        {
            "type": "fact",
            "text": "This record is intentionally erased by the test.",
            "source": "test",
            "confidence": 1,
            "project_id": project_id,
        }
    )

    missing_acknowledgement = client.post(
        "/api/data/core-erase", json={"confirmation": "ERASE_CORE_DATA", "export_acknowledged": False}
    )
    assert missing_acknowledgement.status_code == 422

    erased = client.post(
        "/api/data/core-erase", json={"confirmation": "ERASE_CORE_DATA", "export_acknowledged": True}
    )

    assert erased.status_code == 200
    assert erased.json()["status"] == "core_data_erased"
    assert runtime.database.list_user_projects() == []
    assert runtime.database.list_memories() == []
    assert runtime.projects.get("general").metadata.id == "general"
    try:
        runtime.projects.get(project_id)
    except KeyError:
        pass
    else:
        raise AssertionError("Erased user project remained registered in the active runtime")
    assert "private project-state databases" in " ".join(erased.json()["retained_scopes"])


def test_browser_doctor_report_is_safe_to_share(client: TestClient) -> None:
    response = client.get("/api/doctor")

    assert response.status_code == 200
    report = response.json()
    serialized = json.dumps(report)
    assert report["safe_to_share"] is True
    assert report["providers"]["values_exposed"] is False
    assert report["projects"]["names_exposed"] is False
    assert "tenant_id" not in serialized
    assert "credential values" in report["redaction"].lower()
