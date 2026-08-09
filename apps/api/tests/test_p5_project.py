from __future__ import annotations

from datetime import datetime
from datetime import timedelta, timezone

from fastapi.testclient import TestClient
from personal_ai_os_projects import P5Project


BEIJING = timezone(timedelta(hours=8), "Asia/Shanghai")


def _run_lock(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/projects/p5/daily-run",
        json={
            "result_issue": "26210",
            "official_result": "09431",
            "result_confirmed": True,
            "next_issue": "26211",
            "next_draw_date": "2026-08-10",
            "now_beijing": "2026-08-09T22:23:00+08:00",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_p5_registry_contract_is_isolated(client: TestClient) -> None:
    projects = client.get("/api/projects").json()["items"]
    assert [item["id"] for item in projects] == ["general", "soccer", "p5"]
    detail = client.get("/api/projects/p5").json()
    assert detail["metadata"]["name"] == "P5 / 排列5"
    assert detail["context"]["execution_path"] == "gpt/chatgpt"
    assert detail["context"]["forbidden_execution_path"] == "codex"
    assert detail["permissions"]["denied_projects"] == ["p3"]
    assert detail["context"]["observation_arm"] == "UNQUALIFIED_OBSERVATION_ARM"
    assert detail["context"]["money_staked_cny"] == 0
    assert detail["context"]["live_betting_allowed"] is False
    assert [item["id"] for item in detail["views"]] == [
        "home",
        "history",
        "candidates",
        "audit",
    ]
    general = client.get("/api/projects/general").json()
    serialized_general = str(general).lower()
    assert "p5" not in serialized_general
    assert "排列5" not in serialized_general


def test_p5_waits_before_review_when_result_is_not_confirmed(client: TestClient) -> None:
    response = client.post(
        "/api/projects/p5/daily-run",
        json={
            "result_issue": "26210",
            "result_confirmed": False,
            "next_issue": "26211",
            "next_draw_date": "2026-08-10",
            "now_beijing": "2026-08-09T22:22:00+08:00",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "waiting_for_result"
    assert body["result_confirmed"] is False
    assert body["observation_arm"] == "UNQUALIFIED_OBSERVATION_ARM"
    assert body["money_staked_cny"] == 0
    assert body["live_betting_allowed"] is False
    assert body["retry_at"].endswith("+08:00")
    history_response = client.get("/api/projects/p5/history").json()
    assert history_response["observation_arm"] == "UNQUALIFIED_OBSERVATION_ARM"
    assert history_response["money_staked_cny"] == 0
    assert history_response["live_betting_allowed"] is False
    history = history_response["items"]
    assert history[0]["status"] == "waiting_for_result"
    assert history[0]["candidate_count"] == 0


def test_p5_daily_loop_persists_exactly_10000_and_supports_candidate_audit(
    client: TestClient,
) -> None:
    body = _run_lock(client)
    assert body["status"] == "locked"
    assert body["candidate_count"] == 10_000
    assert len(body["top10"]) == 10
    assert len(body["top5"]) == 5
    assert body["top5"] == body["top10"][:5]
    assert body["execution_path"] == "gpt/chatgpt"
    assert body["codex_invoked"] is False
    assert body["observation_arm"] == "UNQUALIFIED_OBSERVATION_ARM"
    assert body["money_staked_cny"] == 0
    assert body["live_betting_allowed"] is False
    assert body["top10_role"] == "diagnostic_verification_prefix"
    assert body["top5_role"] == "diagnostic_verification_prefix"
    assert body["review"]["metrics"]["candidate_count"] == 0
    assert len(body["review"]["rule_updates"]) == 5
    assert all(
        item["evidence"] == "not_applicable"
        for item in body["review"]["rule_updates"]
    )
    assert not any(item["retuned"] for item in body["review"]["rule_updates"])

    listing = client.get("/api/projects/p5/candidates?issue=26211&limit=100").json()
    assert listing["observation_arm"] == "UNQUALIFIED_OBSERVATION_ARM"
    assert listing["money_staked_cny"] == 0
    assert listing["live_betting_allowed"] is False
    assert listing["candidate_count"] == 10_000
    assert len(listing["items"]) == 100
    required = {
        "generated_order",
        "raw_score",
        "adjusted_score",
        "feature_scores",
        "filters_triggered",
        "elimination_reason",
        "survived_final_filter",
        "final_rank",
        "is_top10",
        "is_top5",
        "model_version",
        "created_at",
    }
    assert required <= set(listing["items"][0])
    assert [item["final_rank"] for item in listing["items"][:10]] == list(range(1, 11))
    assert all(item["is_top10"] for item in listing["items"][:10])
    assert all(item["is_top5"] for item in listing["items"][:5])

    number = listing["items"][37]["number"]
    lookup = client.get(
        f"/api/projects/p5/candidates?issue=26211&number={number}"
    ).json()
    assert lookup["generated"] is True
    assert lookup["candidate"]["number"] == number
    missing = None
    for value in range(100):
        candidate = client.get(
            f"/api/projects/p5/candidates?issue=26211&number={value:05d}"
        ).json()
        if not candidate["generated"]:
            missing = candidate
            break
    assert missing is not None
    assert missing["generated"] is False
    assert missing["candidate"] is None

    audit = client.get("/api/projects/p5/audit").json()
    assert audit["codex_invoked"] is False
    assert audit["observation_arm"] == "UNQUALIFIED_OBSERVATION_ARM"
    assert audit["money_staked_cny"] == 0
    assert audit["live_betting_allowed"] is False
    assert {event["action"] for event in audit["events"]} >= {
        "review.completed",
        "forecast.locked",
    }


def test_p5_lock_is_immutable_and_mcp_tools_are_project_scoped(client: TestClient) -> None:
    first = _run_lock(client)
    second = _run_lock(client)
    assert first["top10"] == second["top10"]
    assert second["candidate_count"] == 10_000

    p5_tools = client.get("/api/mcp/tools?project_id=p5").json()["items"]
    assert {tool["name"] for tool in p5_tools} == {
        "p5.status",
        "p5.history",
        "p5.candidate.lookup",
        "p5.daily.run",
        "p5.audit",
    }
    general_tools = client.get("/api/mcp/tools?project_id=general").json()["items"]
    assert all(not tool["name"].startswith("p5.") for tool in general_tools)
    blocked = client.post(
        "/api/mcp/invoke",
        json={
            "project_id": "general",
            "tool_name": "p5.status",
            "arguments": {},
        },
    )
    assert blocked.status_code == 400
    invoked = client.post(
        "/api/mcp/invoke",
        json={
            "project_id": "p5",
            "tool_name": "p5.candidate.lookup",
            "arguments": {"issue": "26211", "number": first["top10"][0]["number"]},
        },
    )
    assert invoked.status_code == 200
    result = invoked.json()["result"]["content"][0]["json"]
    assert result["generated"] is True


def test_p5_before_2222_waits_for_gate(client: TestClient) -> None:
    response = client.post(
        "/api/projects/p5/daily-run",
        json={
            "result_issue": "26210",
            "official_result": "09431",
            "result_confirmed": True,
            "next_issue": "26211",
            "next_draw_date": "2026-08-10",
            "now_beijing": datetime(2026, 8, 9, 22, 21, tzinfo=BEIJING).isoformat(),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "waiting_for_2222"


def test_p5_rejects_result_and_lock_metadata_conflicts(client: TestClient) -> None:
    _run_lock(client)
    result_conflict = client.post(
        "/api/projects/p5/daily-run",
        json={
            "result_issue": "26210",
            "official_result": "99999",
            "result_confirmed": True,
            "next_issue": "26212",
            "next_draw_date": "2026-08-11",
            "now_beijing": "2026-08-10T22:23:00+08:00",
        },
    )
    assert result_conflict.status_code == 409
    assert "Official result conflict" in result_conflict.json()["detail"]

    lock_conflict = client.post(
        "/api/projects/p5/daily-run",
        json={
            "result_issue": "26210",
            "official_result": "09431",
            "result_confirmed": True,
            "next_issue": "26211",
            "next_draw_date": "2026-08-12",
            "now_beijing": "2026-08-10T22:23:00+08:00",
        },
    )
    assert lock_conflict.status_code == 409
    assert "Immutable lock metadata conflict" in lock_conflict.json()["detail"]


def test_p5_long_term_negative_rule_can_pause_without_disabling_all_scoring(
    client: TestClient,
) -> None:
    _run_lock(client)
    project = client.app.state.runtime.projects.get("p5")
    assert isinstance(project, P5Project)
    with project.store.connect() as connection:
        generated = {
            row["number"]
            for row in connection.execute(
                "SELECT number FROM p5_candidates WHERE issue = '26211'"
            ).fetchall()
        }
        connection.execute(
            """
            UPDATE p5_rules SET positive_count = 0, negative_count = 19
            WHERE rule_id = 'digit_balance'
            """
        )
    missing = next(
        f"{value:05d}"
        for value in range(100_000)
        if f"{value:05d}" not in generated
    )

    response = client.post(
        "/api/projects/p5/daily-run",
        json={
            "result_issue": "26211",
            "official_result": missing,
            "result_confirmed": True,
            "next_issue": "26212",
            "next_draw_date": "2026-08-11",
            "now_beijing": "2026-08-10T22:23:00+08:00",
        },
    )
    assert response.status_code == 200, response.text
    updates = {
        item["rule_id"]: item for item in response.json()["review"]["rule_updates"]
    }
    assert updates["digit_balance"]["observations"] == 20
    assert updates["digit_balance"]["paused"] is True
    assert updates["digit_balance"]["active"] is False
    rules = {
        item["rule_id"]: item
        for item in client.get("/api/projects/p5/audit").json()["rules"]
    }
    assert rules["digit_balance"]["active"] is False
    assert any(item["active"] for item in rules.values())
