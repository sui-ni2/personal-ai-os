from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from .project_handoff import ProjectHandoffService


router = APIRouter(prefix="/api/projects/{project_id}/handoff", tags=["project-handoff"])


def _service(project_id: str, request: Request) -> ProjectHandoffService:
    runtime = request.app.state.runtime
    try:
        runtime.projects.get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProjectHandoffService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    )


@router.get("")
def get_project_handoff(
    project_id: str,
    request: Request,
    mode: Literal["compact", "full"] = Query(default="compact"),
) -> dict[str, object]:
    return _service(project_id, request).build(project_id, mode=mode)
