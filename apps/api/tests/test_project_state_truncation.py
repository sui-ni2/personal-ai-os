from __future__ import annotations

import json

from personal_ai_os.project_state import (
    MAX_CONTEXT_RECORDS,
    ProjectStateService,
)
from personal_ai_os.runtime import Runtime


def _service(runtime: Runtime) -> ProjectStateService:
    runtime.database.migrate()
    return ProjectStateService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    )


def _seed_overflow(service: ProjectStateService, project_id: str) -> None:
    for index in range(MAX_CONTEXT_RECORDS + 5):
        service.put_state(
            project_id=project_id,
            namespace="ns",
            key=f"key-{index:03d}",
            value={"i": index},
            source="test",
        )
        service.append_experience(
            project_id=project_id,
            namespace="ns",
            text=f"experience-{index:03d}",
            source="test",
            confidence=1.0,
        )


def test_snapshot_reports_truncation_when_records_exceed_limit(runtime: Runtime) -> None:
    service = _service(runtime)
    _seed_overflow(service, "overflow")

    snapshot = service.snapshot("overflow")

    assert len(snapshot.states) == MAX_CONTEXT_RECORDS
    assert len(snapshot.experiences) == MAX_CONTEXT_RECORDS
    assert snapshot.truncated is True


def test_snapshot_not_truncated_within_limit(runtime: Runtime) -> None:
    service = _service(runtime)
    service.put_state(
        project_id="small",
        namespace="ns",
        key="only",
        value={"i": 0},
        source="test",
    )

    assert service.snapshot("small").truncated is False


def test_context_json_reports_truncation(runtime: Runtime) -> None:
    """context_json feeds the chat prompt, so a bounded block must report that it is bounded."""
    service = _service(runtime)
    _seed_overflow(service, "prompt")

    payload = json.loads(service.context_json("prompt"))

    assert payload["truncated"] is True
    assert len(payload["states"]) == MAX_CONTEXT_RECORDS
