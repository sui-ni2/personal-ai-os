from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .project_workflow import ProjectWorkflowConflict, ProjectWorkflowService
from .schemas import ProjectWorkflowAdvance, ProjectWorkflowCreate


router = APIRouter(prefix="/api/projects/{project_id}/workflows", tags=["project-workflow"])


def _service(project_id: str, request: Request) -> ProjectWorkflowService:
    runtime = request.app.state.runtime
    try:
        runtime.projects.get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProjectWorkflowService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    )


@router.get("")
def list_project_workflows(project_id: str, request: Request) -> dict[str, object]:
    return {"items": _service(project_id, request).list_workflows(project_id)}


@router.post("", status_code=201)
def create_project_workflow(
    project_id: str,
    payload: ProjectWorkflowCreate,
    request: Request,
) -> dict[str, object]:
    try:
        return _service(project_id, request).create_workflow(
            project_id=project_id,
            workflow_id=payload.workflow_id,
            run_key=payload.run_key,
            steps=payload.steps,
            source=payload.source,
        )
    except ProjectWorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{workflow_id}/{run_key}")
def get_project_workflow(
    project_id: str,
    workflow_id: str,
    run_key: str,
    request: Request,
) -> dict[str, object]:
    item = _service(project_id, request).get_workflow(project_id, workflow_id, run_key)
    if item is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return item


@router.post("/{workflow_id}/{run_key}/advance")
def advance_project_workflow(
    project_id: str,
    workflow_id: str,
    run_key: str,
    payload: ProjectWorkflowAdvance,
    request: Request,
) -> dict[str, object]:
    try:
        return _service(project_id, request).advance_workflow(
            project_id=project_id,
            workflow_id=workflow_id,
            run_key=run_key,
            next_step=payload.next_step,
            expected_version=payload.expected_version,
            evidence=payload.evidence,
            source=payload.source,
        )
    except ProjectWorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{workflow_id}/{run_key}/transitions")
def list_project_workflow_transitions(
    project_id: str,
    workflow_id: str,
    run_key: str,
    request: Request,
) -> dict[str, object]:
    service = _service(project_id, request)
    if service.get_workflow(project_id, workflow_id, run_key) is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "items": service.list_transitions(project_id, workflow_id, run_key)
    }
