from __future__ import annotations

import pytest

from scripts.ci_evidence_collector import collect_ci_evidence


def _metadata(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "workflow_name": "CI",
        "workflow_url": "https://github.com/example/repo/actions/runs/1",
        "job_id": "123",
        "head_sha": "a" * 40,
        "conclusion": "failure",
        "completed_at": "2026-08-30T00:00:00Z",
    }
    value.update(overrides)
    return value


def test_collector_keeps_metadata_and_uses_existing_fail_closed_classifier() -> None:
    result = collect_ci_evidence(_metadata(), "Authorization: Bearer sk-secret-token FAILED test")

    assert result.maintainer_decision == "needs_review"
    assert result.failure_classification is not None
    assert result.failure_classification.classification == "code_or_test_failure"
    assert "sk-secret-token" not in (result.failure_classification.evidence or "")


def test_successful_ci_does_not_infer_merge_approval() -> None:
    result = collect_ci_evidence(_metadata(conclusion="success"), "")

    assert result.failure_classification is None
    assert result.maintainer_decision == "needs_review"


def test_collector_requires_auditable_https_workflow_url() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        collect_ci_evidence(_metadata(workflow_url="http://example.test/run"), "failure")
