import pytest

from scripts.check_internal_versions import (
    changelog_stable_version,
    public_policy_errors,
    readme_stable_version,
    security_stable_line,
    source_version_errors,
)


CHANGELOG = """# Changelog

## [Unreleased]

## [0.3.0] - 2026-08-31

## [0.2.0] - 2026-08-15
"""

README = """# Personal AI OS

Personal AI OS `v0.3.0` is the current stable tagged release.
"""

SECURITY = """# Security Policy

## Supported versions

Security fixes target the current stable `v0.3.x` release line and the current `main` branch.
The `v0.2.x` line and earlier builds are historical and are not guaranteed to receive fixes.

## Reporting a vulnerability

Use private vulnerability reporting.
"""


def test_matching_source_and_public_policy_pass() -> None:
    assert source_version_errors(
        package_version="0.3.0",
        runtime="0.3.0",
        web="0.3.0",
    ) == []
    assert public_policy_errors(
        changelog_text=CHANGELOG,
        readme_text=README,
        security_text=SECURITY,
    ) == []


def test_stale_security_policy_fails() -> None:
    stale = SECURITY.replace("current stable `v0.3.x`", "current stable `v0.2.x`")

    errors = public_policy_errors(
        changelog_text=CHANGELOG,
        readme_text=README,
        security_text=stale,
    )

    assert errors == [
        "SECURITY supported stable line does not match the latest dated CHANGELOG release: "
        "SECURITY=v0.2.x, CHANGELOG=v0.3.0"
    ]


def test_api_web_source_version_mismatch_fails() -> None:
    errors = source_version_errors(
        package_version="0.3.0",
        runtime="0.3.0",
        web="0.2.9",
    )

    assert errors == [
        "web package version does not match the aligned package version: "
        "web=0.2.9, packages=0.3.0"
    ]


@pytest.mark.parametrize(
    ("parser", "text"),
    [
        (changelog_stable_version, "# Changelog\n\n## [Unreleased]\n"),
        (readme_stable_version, "# Personal AI OS\n\nNo stable version statement.\n"),
        (security_stable_line, "# Security Policy\n\n## Reporting a vulnerability\n"),
    ],
)
def test_missing_public_version_metadata_fails_closed(parser, text: str) -> None:
    with pytest.raises(ValueError):
        parser(text)


def test_malformed_source_version_fails_closed() -> None:
    with pytest.raises(ValueError, match="semantic version"):
        source_version_errors(
            package_version="not-a-version",
            runtime="not-a-version",
            web="not-a-version",
        )


def test_historical_security_version_mentions_do_not_cause_false_failure() -> None:
    security = SECURITY + """
## Historical releases

The old `v0.2.x` line is retained only for historical documentation.
"""

    assert public_policy_errors(
        changelog_text=CHANGELOG,
        readme_text=README,
        security_text=security,
    ) == []
