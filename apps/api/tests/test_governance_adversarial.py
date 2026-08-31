from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from personal_ai_os_providers import ProviderTimeout

from personal_ai_os.chat import stream_chat
from personal_ai_os.db import Database
from personal_ai_os.governance import GovernanceService, _arguments_digest
from personal_ai_os.schemas import ChatRequest, ToolActionPreviewRequest


def _confirmed_action(
    database: Database,
    *,
    confirmation_id: str = "confirmation-1",
    project_id: str = "general",
    connector_id: str = "connector-1",
    tool_name: str = "external.echo",
    arguments: dict[str, object] | None = None,
    expires_at: str | None = None,
) -> str:
    database.migrate()
    arguments = arguments or {"message": "approved"}
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO tool_action_confirmations(id, tenant_id, actor_id, project_id, connector_id, tool_name, arguments_digest, preview_json, status, expires_at, created_at, confirmed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, '{}', 'confirmed', ?, ?, ?)",
            (
                confirmation_id,
                database.tenant_id,
                database.actor_id,
                project_id,
                connector_id,
                tool_name,
                _arguments_digest(arguments),
                expires_at or (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return confirmation_id


def test_confirmation_replay_ttl_and_binding_mutations_fail_closed(tmp_path: Path) -> None:
    database = Database(tmp_path / "governance.sqlite3")
    service = GovernanceService(database)
    confirmation = _confirmed_action(database)
    approved = {"message": "approved"}

    assert service.consume_tool_confirmation(
        confirmation_id=confirmation, project_id="general", connector_id="connector-1", tool_name="external.echo", arguments=approved
    )
    assert not service.consume_tool_confirmation(
        confirmation_id=confirmation, project_id="general", connector_id="connector-1", tool_name="external.echo", arguments=approved
    )

    expired = _confirmed_action(
        database,
        confirmation_id="expired",
        expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
    )
    assert not service.consume_tool_confirmation(
        confirmation_id=expired, project_id="general", connector_id="connector-1", tool_name="external.echo", arguments=approved
    )
    for confirmation_id, project_id, connector_id, tool_name, arguments in [
        ("argument", "general", "connector-1", "external.echo", {"message": "mutated"}),
        ("tool", "general", "connector-1", "external.delete", approved),
        ("project", "soccer", "connector-1", "external.echo", approved),
        ("connector", "general", "connector-2", "external.echo", approved),
    ]:
        _confirmed_action(database, confirmation_id=confirmation_id)
        assert not service.consume_tool_confirmation(
            confirmation_id=confirmation_id,
            project_id=project_id,
            connector_id=connector_id,
            tool_name=tool_name,
            arguments=arguments,
        )


def test_confirmation_is_actor_tenant_bound_atomic_and_persists_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "shared.sqlite3"
    owner = Database(path, tenant_id="tenant-a", actor_id="actor-a", sqlite_timeout_seconds=1)
    confirmation = _confirmed_action(owner)
    approved = {"message": "approved"}
    other_actor = GovernanceService(Database(path, tenant_id="tenant-a", actor_id="actor-b", sqlite_timeout_seconds=1))
    other_actor.database.migrate()
    other_tenant = GovernanceService(Database(path, tenant_id="tenant-b", actor_id="actor-a", sqlite_timeout_seconds=1))
    other_tenant.database.migrate()
    assert not other_actor.consume_tool_confirmation(
        confirmation_id=confirmation, project_id="general", connector_id="connector-1", tool_name="external.echo", arguments=approved
    )
    assert not other_tenant.consume_tool_confirmation(
        confirmation_id=confirmation, project_id="general", connector_id="connector-1", tool_name="external.echo", arguments=approved
    )

    owner_service = GovernanceService(owner)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(
            lambda _: owner_service.consume_tool_confirmation(
                confirmation_id=confirmation, project_id="general", connector_id="connector-1", tool_name="external.echo", arguments=approved
            ),
            range(2),
        ))
    assert outcomes.count(True) == 1
    restarted = GovernanceService(Database(path, tenant_id="tenant-a", actor_id="actor-a"))
    assert not restarted.consume_tool_confirmation(
        confirmation_id=confirmation, project_id="general", connector_id="connector-1", tool_name="external.echo", arguments=approved
    )


def test_budget_reservation_allows_only_one_concurrent_request_at_the_limit(tmp_path: Path) -> None:
    database = Database(tmp_path / "budget.sqlite3", sqlite_timeout_seconds=1)
    database.migrate()
    service = GovernanceService(database)
    service.set_budget_policy(
        {"scope_type": "project", "scope_id": "general", "period": "daily", "limit_tokens": 150, "warn_percent": 80, "hard_limit": True}
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        reservations = list(pool.map(
            lambda _: service.reserve_budget("general", tokens=100, reason="concurrency-test"), range(2)
        ))
    assert sum(not item["blocked"] for item in reservations) == 1
    winner = next(item for item in reservations if not item["blocked"])
    assert winner["reservation_id"]
    service.settle_budget_reservation(winner["reservation_id"], status="released")
    assert not service.reserve_budget("general", tokens=100, reason="after-release")["blocked"]


@pytest.mark.asyncio
async def test_unknown_external_outcome_requires_confirmation_and_is_not_replayed(runtime, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime.database.migrate()
    confirmation = _confirmed_action(
        runtime.database,
        connector_id="connector-unknown",
        arguments={"message": "write"},
    )

    async def unknown_result(*_args, **_kwargs):
        raise ProviderTimeout("connector response was lost", code="timeout", retryable=True)

    monkeypatch.setattr(runtime.external_mcp, "invoke", unknown_result)
    events = "".join(
        [
            item
            async for item in stream_chat(
                runtime,
                ChatRequest(
                    provider="openai",
                    model="openai-test",
                    project_id="general",
                    content="Run the approved external write.",
                    tool={
                        "connector_id": "connector-unknown",
                        "name": "external.echo",
                        "arguments": {"message": "write"},
                        "confirmation_id": confirmation,
                    },
                ),
            )
        ]
    )
    assert "event: error" in events
    with runtime.database.connect() as connection:
        row = connection.execute("SELECT status, retry_status, side_effect_status FROM execution_runs").fetchone()
    assert dict(row) == {
        "status": "outcome_unknown",
        "retry_status": "retry_requires_confirmation",
        "side_effect_status": "outcome_unknown",
    }


def test_preview_refuses_unavailable_connector(runtime) -> None:
    runtime.database.migrate()
    with pytest.raises(KeyError):
        GovernanceService(runtime.database).preview_tool_action(
            runtime,
            ToolActionPreviewRequest(
                project_id="general", connector_id="missing", tool_name="external.echo", arguments={"message": "no"}
            ),
        )
