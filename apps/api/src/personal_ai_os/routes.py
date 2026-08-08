from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from .chat import stream_chat
from .runtime import Runtime
from .schemas import ArtifactCreate, ChatRequest, MCPInvokeRequest, MemoryCreate, MemoryUpdate, SettingsUpdate

router = APIRouter(prefix="/api")


def runtime_from(request: Request) -> Runtime:
    return request.app.state.runtime


@router.get("/providers")
def providers(request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    return {"items": runtime.providers.describe()}


@router.get("/projects")
def projects(request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    return {"items": [item.model_dump() for item in runtime.projects.list()]}


@router.get("/projects/{project_id}")
def project_detail(project_id: str, request: Request) -> dict[str, object]:
    try:
        return runtime_from(request).projects.describe(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/conversations")
def conversations(request: Request) -> dict[str, object]:
    return {"items": [item.model_dump(mode="json") for item in runtime_from(request).database.list_conversations()]}


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    if runtime.database.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "items": [item.model_dump(mode="json") for item in runtime.database.list_messages(conversation_id)]
    }


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    return StreamingResponse(
        stream_chat(runtime_from(request), payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/memory")
def list_memory(
    request: Request,
    status: Annotated[str | None, Query(pattern="^(active|inactive)$")] = None,
) -> dict[str, object]:
    return {
        "items": [
            item.model_dump(mode="json") for item in runtime_from(request).database.list_memories(status)
        ]
    }


@router.post("/memory", status_code=201)
def create_memory(payload: MemoryCreate, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    if payload.project_id:
        try:
            runtime.projects.get(payload.project_id)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    item = runtime.database.create_memory(payload.model_dump())
    runtime.database.add_repository_event(
        event_type="memory.created",
        summary=f"Created {item.type} memory",
        project_id=item.project_id,
        details={"memory_id": item.id, "source": item.source},
    )
    return item.model_dump(mode="json")


@router.patch("/memory/{memory_id}")
def update_memory(memory_id: str, payload: MemoryUpdate, request: Request) -> dict[str, object]:
    item = runtime_from(request).database.update_memory(
        memory_id, payload.model_dump(exclude_unset=True)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return item.model_dump(mode="json")


@router.get("/repository/artifacts")
def list_artifacts(request: Request) -> dict[str, object]:
    return {
        "items": [
            item.model_dump(mode="json") for item in runtime_from(request).database.list_artifacts()
        ]
    }


@router.post("/repository/artifacts", status_code=201)
def create_artifact(payload: ArtifactCreate, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    if payload.project_id:
        try:
            runtime.projects.get(payload.project_id)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return runtime.database.create_artifact(payload.model_dump()).model_dump(mode="json")


@router.get("/repository/timeline")
def repository_timeline(request: Request) -> dict[str, object]:
    return {
        "items": [
            item.model_dump(mode="json")
            for item in runtime_from(request).database.list_repository_events()
        ]
    }


@router.get("/mcp/tools")
def list_mcp_tools(request: Request, project_id: str = "general") -> dict[str, object]:
    try:
        items = runtime_from(request).mcp.list_tools(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": [item.model_dump() for item in items]}


@router.post("/mcp/invoke")
async def invoke_mcp(payload: MCPInvokeRequest, request: Request) -> dict[str, object]:
    try:
        result = await runtime_from(request).mcp.invoke(
            payload.project_id, payload.tool_name, payload.arguments
        )
    except (KeyError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"tool": payload.tool_name, "result": result}


@router.get("/settings")
def get_settings(request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    default_provider = runtime.database.get_setting("default_provider") or runtime.settings.default_provider
    default_model = runtime.database.get_setting("default_model") or runtime.settings.default_model
    return {
        "default_provider": default_provider,
        "default_model": default_model,
        "providers": runtime.providers.describe(),
        "mcp": {"servers": [{"id": "local-reference", "configured": True}]},
        "secrets": {"storage": "environment", "values_exposed": False},
    }


@router.patch("/settings")
def update_settings(payload: SettingsUpdate, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    current_provider = runtime.database.get_setting("default_provider") or runtime.settings.default_provider
    current_model = runtime.database.get_setting("default_model") or runtime.settings.default_model
    provider_id = payload.default_provider or current_provider
    try:
        provider = runtime.providers.get(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.default_model:
        model_id = payload.default_model
    elif payload.default_provider and current_model not in provider.models:
        model_id = provider.models[0]
    else:
        model_id = current_model
    if model_id not in provider.models:
        raise HTTPException(status_code=400, detail="Model is not allowlisted for provider")
    runtime.database.set_setting("default_provider", provider_id)
    runtime.database.set_setting("default_model", model_id)
    return get_settings(request)
