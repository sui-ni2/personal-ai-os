from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .project_state import ProjectStateService
from .schemas import ProjectExperienceAppend, ProjectStatePut


router = APIRouter(prefix="/api/projects/{project_id}/state", tags=["project-state"])


def _service(project_id: str, request: Request) -> ProjectStateService:
    runtime = request.app.state.runtime
    try:
        runtime.projects.get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProjectStateService(runtime.database)


@router.get("")
def get_project_state(project_id: str, request: Request) -> dict[str, object]:
    service = _service(project_id, request)
    return service.snapshot(project_id).as_context()


@router.put("/records")
def put_project_state(
    project_id: str,
    payload: ProjectStatePut,
    request: Request,
) -> dict[str, object]:
    service = _service(project_id, request)
    return service.put_state(
        project_id=project_id,
        namespace=payload.namespace,
        key=payload.key,
        value=payload.value,
        source=payload.source,
        confidence=payload.confidence,
    )


@router.post("/experience", status_code=201)
def append_project_experience(
    project_id: str,
    payload: ProjectExperienceAppend,
    request: Request,
) -> dict[str, object]:
    service = _service(project_id, request)
    return service.append_experience(
        project_id=project_id,
        namespace=payload.namespace,
        text=payload.text,
        source=payload.source,
        confidence=payload.confidence,
    )
