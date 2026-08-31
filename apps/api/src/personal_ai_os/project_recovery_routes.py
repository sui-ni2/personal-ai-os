from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .project_recovery import ProjectRecoveryConflict, ProjectRecoveryService
from .schemas import (
    ProjectRecoveryCheckpoint,
    ProjectRecoveryConfirm,
    ProjectRecoverySessionClose,
)


router = APIRouter(prefix="/api/projects/{project_id}/recovery", tags=["project-recovery"])


def _service(project_id: str, request: Request) -> tuple[ProjectRecoveryService, str]:
    runtime = request.app.state.runtime
    try:
        canonical_project_id = runtime.projects.get(project_id).metadata.id
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return (
        ProjectRecoveryService(
            runtime.database,
            data_dir=runtime.settings.data_dir,
            tenant_id=runtime.settings.tenant_id,
        ),
        canonical_project_id,
    )


@router.get("")
def inspect_project_recovery(project_id: str, request: Request) -> dict[str, object]:
    service, canonical_project_id = _service(project_id, request)
    return service.inspect(canonical_project_id)


@router.post("/sessions", status_code=201)
def start_project_recovery_session(
    project_id: str,
    request: Request,
) -> dict[str, object]:
    service, canonical_project_id = _service(project_id, request)
    return service.start_session(canonical_project_id)


@router.post("/sessions/{session_id}/checkpoint")
def checkpoint_project_recovery(
    project_id: str,
    session_id: str,
    payload: ProjectRecoveryCheckpoint,
    request: Request,
) -> dict[str, object]:
    try:
        service, canonical_project_id = _service(project_id, request)
        return service.checkpoint(
            canonical_project_id,
            session_id,
            expected_version=payload.expected_version,
        )
    except ProjectRecoveryConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/preview")
def preview_project_recovery(
    project_id: str,
    session_id: str,
    request: Request,
) -> dict[str, object]:
    try:
        service, canonical_project_id = _service(project_id, request)
        return service.preview(canonical_project_id, session_id)
    except ProjectRecoveryConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/close")
def close_project_recovery_session(
    project_id: str,
    session_id: str,
    payload: ProjectRecoverySessionClose,
    request: Request,
) -> dict[str, object]:
    try:
        service, canonical_project_id = _service(project_id, request)
        return service.close_session(
            canonical_project_id,
            session_id,
            expected_version=payload.expected_version,
        )
    except ProjectRecoveryConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/confirm")
def confirm_project_recovery(
    project_id: str,
    session_id: str,
    payload: ProjectRecoveryConfirm,
    request: Request,
) -> dict[str, object]:
    try:
        service, canonical_project_id = _service(project_id, request)
        return service.confirm_restore(
            canonical_project_id,
            session_id,
            expected_version=payload.expected_version,
        )
    except ProjectRecoveryConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
