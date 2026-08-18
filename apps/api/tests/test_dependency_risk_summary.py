import pytest

from scripts.dependency_risk_summary import summarize_dependency_change


def test_major_toolchain_upgrade_requires_migration() -> None:
    result = summarize_dependency_change(
        package="typescript",
        current_version="5.9.3",
        new_version="7.0.2",
        scope="development",
        affected_surface="web toolchain",
        toolchain_or_framework=True,
        release_notes_url="https://example.com/typescript-7",
    )

    assert result.update_level == "major"
    assert result.risk == "high"
    assert result.review_mode == "migration_required"
    assert "Platform Readiness" in result.required_checks
    assert result.auto_merge_allowed is False
    assert result.decision == "needs_review"


def test_runtime_patch_still_gets_focused_review() -> None:
    result = summarize_dependency_change(
        package="react",
        current_version="19.2.7",
        new_version="19.2.8",
        scope="runtime",
        affected_surface="web runtime",
    )

    assert result.update_level == "patch"
    assert result.risk == "medium"
    assert result.review_mode == "focused_review"
    assert result.required_checks == (
        "CI",
        "Dependency Review",
        "CodeQL",
        "Platform Readiness",
    )


def test_development_patch_is_low_risk_but_never_auto_approved() -> None:
    result = summarize_dependency_change(
        package="some-dev-tool",
        current_version="1.2.3",
        new_version="1.2.4",
        scope="development",
        affected_surface="linting",
    )

    assert result.risk == "low"
    assert result.review_mode == "routine_review"
    assert result.required_checks == ("CI", "Dependency Review")
    assert result.auto_merge_allowed is False


def test_toolchain_minor_update_gets_high_compatibility_review() -> None:
    result = summarize_dependency_change(
        package="@cloudflare/vite-plugin",
        current_version="1.51.3",
        new_version="1.52.1",
        scope="development",
        affected_surface="hosted build",
        toolchain_or_framework=True,
    )

    assert result.update_level == "minor"
    assert result.risk == "high"
    assert result.review_mode == "compatibility_review"
    assert "Platform Readiness" in result.required_checks


def test_runtime_minor_update_gets_compatibility_review() -> None:
    result = summarize_dependency_change(
        package="runtime-lib",
        current_version="3.1.0",
        new_version="3.2.0",
        scope="runtime",
        affected_surface="API runtime",
    )

    assert result.update_level == "minor"
    assert result.risk == "medium"
    assert result.review_mode == "compatibility_review"


def test_prerelease_transition_is_high_risk() -> None:
    result = summarize_dependency_change(
        package="framework",
        current_version="2.0.0",
        new_version="2.0.0-beta.1",
        scope="runtime",
        affected_surface="web runtime",
    )

    assert result.update_level == "prerelease"
    assert result.risk == "high"
    assert result.review_mode == "compatibility_review"


def test_downgrade_is_blocked_change() -> None:
    result = summarize_dependency_change(
        package="runtime-lib",
        current_version="3.2.0",
        new_version="3.1.9",
        scope="runtime",
        affected_surface="API runtime",
    )

    assert result.update_level == "downgrade"
    assert result.risk == "high"
    assert result.review_mode == "blocked_change"


def test_same_version_reports_no_change() -> None:
    result = summarize_dependency_change(
        package="dev-tool",
        current_version="1.2.3",
        new_version="1.2.3",
        scope="development",
        affected_surface="tests",
    )

    assert result.update_level == "same"
    assert result.review_mode == "no_change"


def test_invalid_semver_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported semantic version"):
        summarize_dependency_change(
            package="package",
            current_version="latest",
            new_version="2.0.0",
            scope="development",
            affected_surface="tooling",
        )


def test_non_https_release_notes_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        summarize_dependency_change(
            package="package",
            current_version="1.0.0",
            new_version="1.0.1",
            scope="development",
            affected_surface="tooling",
            release_notes_url="http://example.com/release",
        )
