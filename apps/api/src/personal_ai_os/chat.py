from __future__ import annotations

import json
from collections.abc import AsyncIterator
from time import perf_counter
from uuid import uuid4

from personal_ai_os_core import EventType, ExecutionEvent, Message, MessageRole

from .runtime import Runtime
from .schemas import ChatRequest


def _sse(event: ExecutionEvent) -> str:
    payload = event.public_payload()
    return f"event: {event.type.value}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _event(
    runtime: Runtime,
    *,
    event_type: EventType,
    status: str,
    conversation_id: str,
    tool: str | None = None,
    duration_ms: int | None = None,
    payload: dict[str, object] | None = None,
) -> ExecutionEvent:
    event = ExecutionEvent(
        id=str(uuid4()),
        type=event_type,
        status=status,
        conversation_id=conversation_id,
        tool=tool,
        duration_ms=duration_ms,
        payload=payload or {},
    )
    runtime.database.add_execution_event(event.model_dump(mode="json"))
    return event


async def stream_chat(runtime: Runtime, request: ChatRequest) -> AsyncIterator[str]:
    started = perf_counter()
    conversation = (
        runtime.database.get_conversation(request.conversation_id) if request.conversation_id else None
    )
    if request.conversation_id and not conversation:
        event = ExecutionEvent(
            id=str(uuid4()),
            type=EventType.ERROR,
            status="failed",
            conversation_id=request.conversation_id,
            payload={"message": "Conversation not found"},
        )
        yield _sse(event)
        return

    try:
        project = runtime.projects.get(request.project_id)
        provider = runtime.providers.get(request.provider)
    except KeyError as exc:
        event = ExecutionEvent(
            id=str(uuid4()),
            type=EventType.ERROR,
            status="failed",
            conversation_id=request.conversation_id,
            payload={"message": str(exc)},
        )
        yield _sse(event)
        return

    if conversation is None:
        conversation = runtime.database.create_conversation(
            provider=request.provider,
            model=request.model,
            project_id=request.project_id,
            title=request.content.strip().splitlines()[0],
        )
    elif conversation.project_id != request.project_id:
        error = _event(
            runtime,
            event_type=EventType.ERROR,
            status="failed",
            conversation_id=conversation.id,
            payload={"message": "A conversation cannot change project context"},
        )
        yield _sse(error)
        return
    else:
        runtime.database.update_conversation_route(conversation.id, request.provider, request.model)

    runtime.database.add_message(conversation.id, MessageRole.USER, request.content)
    tool_ref: list[str] = []

    try:
        if request.tool:
            tool_started = perf_counter()
            start_event = _event(
                runtime,
                event_type=EventType.TOOL_START,
                status="started",
                conversation_id=conversation.id,
                tool=request.tool.name,
                payload={"server": "allowlisted", "arguments": sorted(request.tool.arguments)},
            )
            yield _sse(start_event)
            result = await runtime.mcp.invoke(request.project_id, request.tool.name, request.tool.arguments)
            tool_ref.append(request.tool.name)
            duration = int((perf_counter() - tool_started) * 1000)
            result_event = _event(
                runtime,
                event_type=EventType.TOOL_RESULT,
                status="succeeded",
                conversation_id=conversation.id,
                tool=request.tool.name,
                duration_ms=duration,
                payload={"result": result},
            )
            yield _sse(result_event)
            runtime.database.add_repository_event(
                event_type="tool.completed",
                summary=f"Completed {request.tool.name}",
                project_id=request.project_id,
                details={"conversation_id": conversation.id, "duration_ms": duration},
            )

        history = runtime.database.list_messages(conversation.id)
        system_message = Message(
            id="project-context",
            conversation_id=conversation.id,
            role=MessageRole.SYSTEM,
            content=(
                "Project context (configuration, not user content): "
                + json.dumps(project.context(), ensure_ascii=False)
            ),
        )
        if request.tool:
            history.append(
                Message(
                    id="tool-result",
                    conversation_id=conversation.id,
                    role=MessageRole.SYSTEM,
                    content="Verified tool result: " + json.dumps(result, ensure_ascii=False),
                    tool_refs=tool_ref,
                )
            )

        chunks: list[str] = []
        async for chunk in provider.stream([system_message, *history], request.model):
            chunks.append(chunk)
            message_event = _event(
                runtime,
                event_type=EventType.MESSAGE,
                status="running",
                conversation_id=conversation.id,
                payload={"delta": chunk},
            )
            yield _sse(message_event)

        assistant = runtime.database.add_message(
            conversation.id,
            MessageRole.ASSISTANT,
            "".join(chunks),
            tool_refs=tool_ref,
        )
        done = _event(
            runtime,
            event_type=EventType.DONE,
            status="succeeded",
            conversation_id=conversation.id,
            duration_ms=int((perf_counter() - started) * 1000),
            payload={"message_id": assistant.id, "conversation_id": conversation.id},
        )
        yield _sse(done)
    except Exception as exc:
        error = _event(
            runtime,
            event_type=EventType.ERROR,
            status="failed",
            conversation_id=conversation.id,
            duration_ms=int((perf_counter() - started) * 1000),
            payload={"message": str(exc)},
        )
        yield _sse(error)
        done = _event(
            runtime,
            event_type=EventType.DONE,
            status="failed",
            conversation_id=conversation.id,
            duration_ms=int((perf_counter() - started) * 1000),
            payload={"conversation_id": conversation.id},
        )
        yield _sse(done)
