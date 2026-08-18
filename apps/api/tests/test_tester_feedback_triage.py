import pytest

from scripts.tester_feedback_triage import triage_feedback


def test_setup_failure_routes_to_setup_friction() -> None:
    result = triage_feedback(
        "Fresh clone setup failed on Ubuntu after docker compose up --build -d."
    )

    assert result.category == "setup_friction"
    assert result.needs_reproduction is True
    assert result.adoption_evidence is False
    assert result.decision == "needs_review"


def test_documentation_gap_is_distinct_from_product_bug() -> None:
    result = triage_feedback("The README instructions are unclear around the no-key startup path.")

    assert result.category == "documentation_gap"
    assert result.needs_reproduction is False


def test_product_bug_requests_reproduction() -> None:
    result = triage_feedback("After restart the project memory is lost and the workflow is broken.")

    assert result.category == "product_bug"
    assert result.needs_reproduction is True


def test_feature_request_is_not_adoption_evidence() -> None:
    result = triage_feedback("Feature request: please add support for another local provider.")

    assert result.category == "feature_request"
    assert result.adoption_evidence is False
    assert result.needs_maintainer_review is True


def test_use_outcome_still_requires_review_before_adoption_claim() -> None:
    result = triage_feedback("I tested the memory workflow for a project and it worked for my use case.")

    assert result.category == "use_outcome"
    assert result.adoption_evidence is False
    assert result.decision == "needs_review"


def test_unknown_feedback_fails_closed() -> None:
    result = triage_feedback("Interesting project, thanks for sharing.")

    assert result.category == "inconclusive"
    assert result.confidence == "low"
    assert result.adoption_evidence is False
    assert result.evidence is None


def test_secret_shapes_are_redacted_from_evidence() -> None:
    result = triage_feedback(
        "The setup failed with Authorization: Bearer secret-token ghp_1234567890abcdef sk-abcdefghijk"
    )

    assert result.evidence is not None
    assert "secret-token" not in result.evidence
    assert "ghp_1234567890abcdef" not in result.evidence
    assert "sk-abcdefghijk" not in result.evidence
    assert result.privacy_redactions_applied is True


def test_env_secret_shape_is_redacted() -> None:
    result = triage_feedback("Setup error after OPENAI_KEY=super-secret-value was configured.")

    assert result.evidence is not None
    assert "super-secret-value" not in result.evidence
    assert result.privacy_redactions_applied is True


def test_https_source_url_is_preserved() -> None:
    result = triage_feedback(
        "The guide is confusing for Docker setup.",
        source_url="https://github.com/example/repo/issues/1",
    )

    assert result.source_url == "https://github.com/example/repo/issues/1"


def test_non_https_source_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        triage_feedback("Setup failed.", source_url="http://example.com/report")
