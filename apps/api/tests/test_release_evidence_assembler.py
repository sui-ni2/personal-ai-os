from __future__ import annotations

from datetime import datetime, timezone

import pytest

from scripts.release_evidence_assembler import assemble_release_evidence
from scripts.release_evidence_verifier import REQUIRED_CHECKS, verify_release_evidence


SHA = "a" * 40


def _check(name: str) -> dict[str, str]:
    return {
        "name": name,
        "conclusion": "success",
        "head_sha": SHA,
        "completed_at": "2026-08-30T00:00:00Z",
        "details_url": f"https://github.com/example/repo/actions/runs/{name}",
    }


def test_assembler_normalizes_only_required_check_fields_for_the_verifier() -> None:
    bundle = assemble_release_evidence(
        {"checks": [_check(name) for name in REQUIRED_CHECKS] + [{"name": "unrelated"}]},
        expected_sha=SHA,
    )

    assert bundle["commit_sha"] == SHA
    assert [item["name"] for item in bundle["checks"]] == list(REQUIRED_CHECKS)
    result = verify_release_evidence(
        bundle,
        expected_sha=SHA,
        as_of=datetime(2026, 8, 30, 1, tzinfo=timezone.utc),
    )
    assert result.ready_to_tag is True


def test_assembler_does_not_invent_missing_required_checks() -> None:
    bundle = assemble_release_evidence({"checks": [_check("CI")]}, expected_sha=SHA)

    assert bundle["checks"] == [
        {
            "name": "CI",
            "conclusion": "success",
            "head_sha": SHA,
            "completed_at": "2026-08-30T00:00:00Z",
            "url": "https://github.com/example/repo/actions/runs/CI",
        }
    ]


def test_assembler_requires_full_expected_sha() -> None:
    with pytest.raises(ValueError, match="40-character"):
        assemble_release_evidence({"checks": []}, expected_sha="abc")
