from __future__ import annotations

import json

import pytest
from personal_ai_os_core import EventType, ExecutionEvent
from personal_ai_os_mcp import MCPInvocationError

from personal_ai_os.project_state_mcp import PROJECT_STATE_TOOL_NAMES


@pytest.mark.asyncio
async def test_private_state_tools_are_enabled_for_soccer_and_p5_only(runtime) -> None:
    soccer_tools = {tool.name for tool in runtime.mcp.list_tools("soccer")}
    p5_tools = {tool.name for tool in runtime.mcp.list_tools("p5")}
    general_tools = {tool.name for tool in runtime.mcp.list_tools("general")}

    assert PROJECT_STATE_TOOL_NAMES.issubset(soccer_tools)
    assert PROJECT_STATE_TOOL_NAMES.issubset(p5_tools)
    assert PROJECT_STATE_TOOL_NAMES.isdisjoint(general_tools)
    assert "system.echo" in general_tools
    assert runtime.mcp.audit_result_policy("soccer", "project.state.snapshot") == "metadata_only"
    assert runtime.mcp.audit_result_policy("p5", "project.workflow.list") == "metadata_only"
    assert runtime.mcp.audit_result_policy("general", "system.echo") == "bounded"


@pytest.mark.asyncio
async def test_mcp_state_is_bound_to_active_project_and_cannot_cross_read(runtime) -> None:
    runtime.database.migrate()
    written = await runtime.mcp.invoke(
        "soccer",
        "project.state.put",
        {
            "namespace": "formal",
            "key": "latest",
            "value": {"record": "synthetic-soccer"},
            "source": "test",
            "confidence": 1,
            "lock": True,
            "expected_version": 0,
        },
    )
    payload = written["content"][0]["json"]
    assert payload["project_id"] == "soccer"
    assert payload["status"] == "locked"
    assert written["_audit_policy"] == "metadata_only"

    soccer = await runtime.mcp.invoke("soccer", "project.state.snapshot", {})
    p5 = await runtime.mcp.invoke("p5", "project.state.snapshot", {})
    soccer_json = soccer["content"][0]["json"]
    p5_json = p5["content"][0]["json"]

    assert soccer_json["project_id"] == "soccer"
    assert soccer_json["states"][0]["value"] == {"record": "synthetic-soccer"}
    assert p5_json["project_id"] == "p5"
    assert p5_json["states"] == []


@pytest.mark.asyncio
async def test_metadata_only_private_result_is_available_to_provider_but_not_audit(runtime) -> None:
    runtime.database.migrate()
    await runtime.mcp.invoke(
        "soccer",
        "project.state.put",
        {
            "namespace": "private",
            "key": "synthetic",
            "value": {"sensitive_value": "do-not-copy-to-audit"},
            "source": "test",
            "expected_version": 0,
        },
    )
    raw_result = await runtime.mcp.invoke("soccer", "project.state.snapshot", {})
    assert "do-not-copy-to-audit" in json.dumps(raw_result)

    event = ExecutionEvent(
        id="private-tool-result",
        type=EventType.TOOL_RESULT,
        status="succeeded",
        conversation_id="synthetic-conversation",
        tool="project.state.snapshot",
        payload={"result": raw_result},
    )
    serialized = json.dumps(event.public_payload())
    assert "do-not-copy-to-audit" not in serialized
    assert "private result omitted from audit" in serialized


@pytest.mark.asyncio
async def test_mcp_rejects_model_supplied_project_override(runtime) -> None:
    runtime.database.migrate()
    with pytest.raises(MCPInvocationError, match="unknown arguments"):
        await runtime.mcp.invoke(
            "soccer",
            "project.state.put",
            {
                "project_id": "p5",
                "namespace": "workflow",
                "key": "current",
                "value": {"stage": "synthetic"},
                "source": "test",
                "expected_version": 0,
            },
        )

    p5 = await runtime.mcp.invoke("p5", "project.state.snapshot", {})
    assert p5["content"][0]["json"]["states"] == []


@pytest.mark.asyncio
async def test_mcp_lock_and_stale_version_fail_closed(runtime) -> None:
    runtime.database.migrate()
    first = await runtime.mcp.invoke(
        "soccer",
        "project.state.put",
        {
            "namespace": "formal",
            "key": "day",
            "value": {"version": "one"},
            "source": "window-a",
            "lock": True,
            "expected_version": 0,
        },
    )
    assert first["content"][0]["json"]["version"] == 1

    with pytest.raises(MCPInvocationError, match="locked"):
        await runtime.mcp.invoke(
            "soccer",
            "project.state.put",
            {
                "namespace": "formal",
                "key": "day",
                "value": {"version": "accidental"},
                "source": "window-b",
                "expected_version": 1,
            },
        )

    replaced = await runtime.mcp.invoke(
        "soccer",
        "project.state.put",
        {
            "namespace": "formal",
            "key": "day",
            "value": {"version": "two"},
            "source": "window-b",
            "lock": True,
            "expected_version": 1,
            "supersede_locked": True,
        },
    )
    assert replaced["content"][0]["json"]["version"] == 2

    with pytest.raises(MCPInvocationError, match="version mismatch"):
        await runtime.mcp.invoke(
            "soccer",
            "project.state.put",
            {
                "namespace": "formal",
                "key": "day",
                "value": {"version": "stale"},
                "source": "window-a",
                "expected_version": 1,
                "supersede_locked": True,
            },
        )


@pytest.mark.asyncio
async def test_mcp_workflow_cannot_skip_gate_and_is_project_isolated(runtime) -> None:
    runtime.database.migrate()
    created = await runtime.mcp.invoke(
        "soccer",
        "project.workflow.create",
        {
            "workflow_id": "daily",
            "run_key": "synthetic",
            "steps": ["review", "input", "formal", "complete"],
            "source": "test",
        },
    )
    assert created["content"][0]["json"]["next_step"] == "review"

    with pytest.raises(MCPInvocationError, match="required next step"):
        await runtime.mcp.invoke(
            "soccer",
            "project.workflow.advance",
            {
                "workflow_id": "daily",
                "run_key": "synthetic",
                "next_step": "formal",
                "expected_version": 1,
                "evidence": {"receipt": "synthetic"},
                "source": "test",
            },
        )

    advanced = await runtime.mcp.invoke(
        "soccer",
        "project.workflow.advance",
        {
            "workflow_id": "daily",
            "run_key": "synthetic",
            "next_step": "review",
            "expected_version": 1,
            "evidence": {"receipt": "verified"},
            "source": "test",
        },
    )
    assert advanced["content"][0]["json"]["next_step"] == "input"

    p5_workflows = await runtime.mcp.invoke("p5", "project.workflow.list", {})
    assert p5_workflows["content"][0]["json"]["items"] == []
