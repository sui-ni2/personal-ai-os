from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from personal_ai_os_projects import P5Project
from pydantic import BaseModel, ConfigDict, Field


router = APIRouter(prefix="/api/projects/p5", tags=["p5-project"])


class P5DailyRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_issue: str = Field(pattern=r"^[0-9]{5,12}$")
    next_issue: str = Field(pattern=r"^[0-9]{5,12}$")
    next_draw_date: str
    official_result: str | None = Field(default=None, pattern=r"^[0-9]{5}$")
    result_confirmed: bool = False
    now_beijing: datetime | None = None


def _project(request: Request) -> P5Project:
    try:
        project = request.app.state.runtime.projects.get("p5")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="P5 project is not registered") from exc
    if not isinstance(project, P5Project):
        raise HTTPException(status_code=500, detail="P5 project registration is invalid")
    return project


@router.get("/home")
def p5_home(request: Request) -> dict[str, object]:
    return _project(request).store.home()


@router.get("/history")
def p5_history(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, object]:
    store = _project(request).store
    return {"items": store.history(limit), **store.research_boundary()}


@router.get("/candidates")
def p5_candidates(
    request: Request,
    issue: Annotated[str, Query(pattern=r"^[0-9]{5,12}$")],
    number: Annotated[str | None, Query(pattern=r"^[0-9]{5}$")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, object]:
    return _project(request).store.candidate(issue, number, limit)


@router.get("/audit")
def p5_audit(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, object]:
    return _project(request).store.audit(limit)


@router.post("/daily-run")
def p5_daily_run(payload: P5DailyRunRequest, request: Request) -> dict[str, object]:
    try:
        return _project(request).store.run_daily(**payload.model_dump())
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
