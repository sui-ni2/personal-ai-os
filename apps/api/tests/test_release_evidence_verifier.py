from datetime import datetime, timezone

import pytest

from scripts.release_evidence_verifier import REQUIRED_CHECKS, verify_release_evidence


SHA = "a" * 40
AS_OF = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def _check(name: str, **overrides: object) -> dict[str, object]:
    check: dict[str, object] = {
        "name": name,
        "conclusion": "success",
        "head_sha": SHA,
        "completed_at": "2026-08-18T11:00:00Z",
        "url": f"https://github.com/example/repo/actions/runs/{name.replace(' ', '-')}",
    }
    check.update(overrides)
    return check


def _payload(checks: list[dict[str, object]] | None = None, *, commit_sha: str = SHA):
    return {
        "commit_sha": commit_sha,
        "checks": checks if checks is not None else [_check(name) for name in REQUIRED_CHECKS],
    }


def _codes(result) -> set[tuple[str, str | None]]:
    return {(blocker.code, blocker.check) for blocker in result.blockers}


def test_complete_fresh_same_commit_bundle_is_ready() -> None:
    result = verify_release_evidence(_payload(), expected_sha=SHA, as_of=AS_OF)

    assert result.ready_to_tag is True
    assert result.decision == "ready_to_tag"
    assert result.blockers == ()


def test_missing_required_check_blocks_release() -> None:
    checks = [_check(name) for name in REQUIRED_CHECKS if name != "CodeQL"]
    result = verify_release_evidence(_payload(checks), expected_sha=SHA, as_of=AS_OF)

    assert result.ready_to_tag is False
    assert ("missing_check", "CodeQL") in _codes(result)


def test_skipped_release_smoke_blocks_release() -> None:
    checks = [
        _check(name, conclusion="skipped") if name == "Release provider smoke" else _check(name)
        for name in REQUIRED_CHECKS
    ]
    result = verify_release_evidence(_payload(checks), expected_sha=SHA, as_of=AS_OF)

    assert ("check_not_successful", "Release provider smoke") in _codes(result)
    assert result.decision == "blocked"


def test_check_from_different_commit_blocks_release() -> None:
    checks = [
        _check(name, head_sha="b" * 40) if name == "CI" else _check(name)
        for name in REQUIRED_CHECKS
    ]
    result = verify_release_evidence(_payload(checks), expected_sha=SHA, as_of=AS_OF)

    assert ("check_commit_mismatch", "CI") in _codes(result)


def test_stale_check_blocks_release() -> None:
    checks = [
        _check(name, completed_at="2026-08-15T00:00:00Z") if name == "Platform Readiness" else _check(name)
        for name in REQUIRED_CHECKS
    ]
    result = verify_release_evidence(
        _payload(checks),
        expected_sha=SHA,
        as_of=AS_OF,
        max_age_hours=48,
    )

    assert ("stale_check", "Platform Readiness") in _codes(result)


def test_duplicate_required_check_blocks_release() -> None:
    checks = [_check(name) for name in REQUIRED_CHECKS]
    checks.append(_check("CodeQL"))
    result = verify_release_evidence(_payload(checks), expected_sha=SHA, as_of=AS_OF)

    assert ("duplicate_check", "CodeQL") in _codes(result)


def test_missing_audit_url_blocks_release() -> None:
    checks = [
        _check(name, url="") if name == "Dependency Review" else _check(name)
        for name in REQUIRED_CHECKS
    ]
    result = verify_release_evidence(_payload(checks), expected_sha=SHA, as_of=AS_OF)

    assert ("missing_source_url", "Dependency Review") in _codes(result)


def test_bundle_commit_mismatch_blocks_release() -> None:
    result = verify_release_evidence(
        _payload(commit_sha="b" * 40),
        expected_sha=SHA,
        as_of=AS_OF,
    )

    assert ("bundle_commit_mismatch", None) in _codes(result)


def test_future_check_blocks_release() -> None:
    checks = [
        _check(name, completed_at="2026-08-18T13:00:00Z") if name == "CI" else _check(name)
        for name in REQUIRED_CHECKS
    ]
    result = verify_release_evidence(_payload(checks), expected_sha=SHA, as_of=AS_OF)

    assert ("future_check", "CI") in _codes(result)


def test_expected_sha_requires_full_commit_sha() -> None:
    with pytest.raises(ValueError, match="40-character"):
        verify_release_evidence(_payload(), expected_sha="abc123", as_of=AS_OF)
