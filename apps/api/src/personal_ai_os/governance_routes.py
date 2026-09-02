from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .governance import GovernanceService
from .routes import runtime_from
from .schemas import (
    BudgetPolicyUpdate,
    ChatRequest,
    SendScopePreviewRequest,
    ToolActionConfirmation,
    ToolActionPreviewRequest,
    RoutingSettingsUpdate,
)


router = APIRouter(prefix="/api")


def _service(request: Request) -> GovernanceService:
    return GovernanceService(runtime_from(request).database)


@router.post("/send-scope/preview")
def preview_send_scope(payload: SendScopePreviewRequest, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    try:
        runtime.projects.get(payload.project_id)
        provider = runtime.providers.get(payload.provider)
        if payload.model not in provider.models:
            raise ValueError("Model is not allowlisted for provider")
        return _service(request).send_scope_preview(runtime, ChatRequest(**payload.model_dump()))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/send-scope/{receipt_id}")
def get_send_scope(receipt_id: str, request: Request) -> dict[str, object]:
    item = _service(request).get_send_scope(receipt_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Send-scope receipt not found")
    return item


@router.get("/usage")
def usage_summary(request: Request, project_id: str | None = None) -> dict[str, object]:
    return _service(request).usage_summary(project_id)


@router.get("/routing")
def routing_settings(request: Request) -> dict[str, object]:
    return _service(request).routing_settings()


@router.put("/routing")
def update_routing(payload: RoutingSettingsUpdate, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    if (payload.fallback_provider is None) != (payload.fallback_model is None):
        raise HTTPException(status_code=400, detail="Fallback provider and model must be configured together")
    if payload.fallback_provider and payload.fallback_model:
        try:
            provider = runtime.providers.get(payload.fallback_provider)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if payload.fallback_model not in provider.models:
            raise HTTPException(status_code=400, detail="Fallback model is not allowlisted")
    result = _service(request).set_routing_settings(payload.model_dump())
    runtime.database.add_repository_event(
        event_type="settings.routing_updated",
        summary="Updated AI service fallback policy",
        details={"policy": payload.policy, "fallback_configured": bool(payload.fallback_provider)},
    )
    return result


@router.get("/budgets")
def budget_status(request: Request, project_id: str = "general") -> dict[str, object]:
    return _service(request).budget_status(project_id)


@router.put("/budgets")
def set_budget(payload: BudgetPolicyUpdate, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    if payload.scope_type == "project":
        try:
            runtime.projects.get(payload.scope_id)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        result = _service(request).set_budget_policy(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    runtime.database.add_repository_event(
        event_type="settings.budget_updated",
        summary="Updated a usage budget policy",
        project_id=payload.scope_id if payload.scope_type == "project" else None,
        details={
            "scope_type": payload.scope_type,
            "period": payload.period,
            "hard_limit": payload.hard_limit,
            "limit_tokens": payload.limit_tokens,
        },
    )
    return result


@router.post("/tool-actions/preview", status_code=201)
def preview_tool_action(payload: ToolActionPreviewRequest, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    try:
        runtime.projects.get(payload.project_id)
        return _service(request).preview_tool_action(runtime, payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tool-actions/{confirmation_id}/confirm")
def confirm_tool_action(
    confirmation_id: str,
    payload: ToolActionConfirmation,
    request: Request,
) -> dict[str, object]:
    del payload
    item = _service(request).confirm_tool_action(confirmation_id)
    if item is None:
        raise HTTPException(status_code=409, detail="Tool action confirmation is missing, expired, or already used")
    return item


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str, request: Request) -> dict[str, object]:
    item = _service(request).get_execution_run(execution_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Execution receipt not found")
    return item


@router.get("/conversations/{conversation_id}/executions")
def list_conversation_executions(conversation_id: str, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    if runtime.database.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"items": _service(request).list_execution_runs(conversation_id)}
