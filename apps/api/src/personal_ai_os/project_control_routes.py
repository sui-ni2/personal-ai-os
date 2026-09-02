from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .governance import GovernanceService
from .project_recovery import ProjectRecoveryService
from .project_state import ProjectStateService
from .routes import runtime_from


router = APIRouter(prefix="/api/projects/{project_id}/control-center")


def _state_groups(items: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    groups = {
        "goals": [], "current_state": [], "tasks": [], "decisions": [], "outcomes": [],
        "blockers": [], "next_actions": [], "changed_files": [], "other": [],
    }
    aliases = {
        "goal": "goals", "goals": "goals", "current": "current_state", "current_state": "current_state",
        "task": "tasks", "tasks": "tasks", "decision": "decisions", "decisions": "decisions",
        "outcome": "outcomes", "outcomes": "outcomes", "blocker": "blockers", "blockers": "blockers",
        "next_action": "next_actions", "next-action": "next_actions", "file": "changed_files", "files": "changed_files",
    }
    for item in items:
        groups[aliases.get(str(item["namespace"]), "other")].append(item)
    return groups


@router.get("")
def project_control_center(project_id: str, request: Request) -> dict[str, object]:
    runtime = runtime_from(request)
    try:
        project = runtime.projects.describe(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    state = ProjectStateService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    )
    groups = _state_groups(state.list_state(project_id))
    activity = [
        item.model_dump(mode="json")
        for item in runtime.database.list_repository_events()
        if item.project_id == project_id
    ][:12]
    files = [
        item.model_dump(mode="json")
        for item in runtime.database.list_artifacts()
        if item.project_id == project_id and item.kind == "file"
    ][:20]
    conversations = runtime.database.list_conversations(project_id=project_id)
    latest_conversation = conversations[0].id if conversations else None
    latest_execution = (
        GovernanceService(runtime.database).list_execution_runs(latest_conversation)[0]
        if latest_conversation and GovernanceService(runtime.database).list_execution_runs(latest_conversation)
        else None
    )
    recovery = ProjectRecoveryService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    ).inspect(project_id)
    memories = GovernanceService(runtime.database).reviewed_memories(project_id)
    return {
        "project": project,
        "state": groups,
        "files": files,
        "activity": activity,
        "recent_execution": latest_execution,
        "recovery": recovery,
        "reviewed_memory": [
            {"id": item["id"], "type": item["type"], "source": item["source"]}
            for item in memories
        ],
        "continuity": {
            "conversation_count": len(conversations),
            "state_record_count": sum(len(items) for items in groups.values()),
            "provider_session_copied": False,
        },
    }
