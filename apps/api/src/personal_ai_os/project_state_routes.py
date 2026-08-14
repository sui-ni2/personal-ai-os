from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from .project_state import ProjectStateConflict, ProjectStateService
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


@router.get("/history")
def get_project_state_history(
    project_id: str,
    request: Request,
    namespace: str | None = Query(default=None, max_length=80),
    key: str | None = Query(default=None, max_length=120),
) -> dict[str, object]:
    service = _service(project_id, request)
    return {"items": service.list_history(project_id, namespace=namespace, key=key)}


@router.put("/records")
def put_project_state(
    project_id: str,
    payload: ProjectStatePut,
    request: Request,
) -> dict[str, object]:
    service = _service(project_id, request)
    try:
        return service.put_state(
            project_id=project_id,
            namespace=payload.namespace,
            key=payload.key,
            value=payload.value,
            source=payload.source,
            confidence=payload.confidence,
            lock=payload.lock,
            expected_version=payload.expected_version,
            supersede_locked=payload.supersede_locked,
        )
    except ProjectStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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
