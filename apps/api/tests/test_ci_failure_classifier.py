from scripts.ci_failure_classifier import classify_failure


def test_classifies_github_sarif_service_failure_as_external() -> None:
    result = classify_failure(
        """
        CodeQL scanned 55 out of 55 Python files.
        Uploading code scanning results
        ##[error]No server is currently available to service your request. Sorry about that.
        """,
        workflow_url="https://github.com/example/repo/actions/runs/1",
        job_id="123",
    )

    assert result.classification == "external_service_failure"
    assert result.confidence == "high"
    assert result.retry_recommended is True
    assert result.decision == "needs_review"
    assert result.rule_id == "github-service-unavailable"
    assert result.workflow_url is not None
    assert result.job_id == "123"


def test_specific_external_failure_outranks_generic_failure_text() -> None:
    result = classify_failure(
        """
        FAILED some earlier helper step
        ##[error]No server is currently available to service your request.
        """
    )

    assert result.classification == "external_service_failure"
    assert result.retry_recommended is True


def test_classifies_repository_workflow_configuration_failure() -> None:
    result = classify_failure("Invalid workflow file: .github/workflows/ci.yml#L12")

    assert result.classification == "repository_configuration_failure"
    assert result.confidence == "high"
    assert result.retry_recommended is False


def test_classifies_dependency_resolution_failure() -> None:
    result = classify_failure("ERR_PNPM_NO_MATCHING_VERSION No matching version found")

    assert result.classification == "dependency_or_install_failure"
    assert result.confidence == "medium"
    assert result.retry_recommended is False


def test_classifies_test_failure_without_claiming_merge_safety() -> None:
    result = classify_failure("tests/test_api.py::test_health FAILED\nAssertionError: expected 200")

    assert result.classification == "code_or_test_failure"
    assert result.decision == "needs_review"
    assert result.retry_recommended is False


def test_unknown_failure_fails_closed() -> None:
    result = classify_failure("runner stopped for an unrecognized reason")

    assert result.classification == "inconclusive"
    assert result.confidence == "low"
    assert result.decision == "needs_review"
    assert result.retry_recommended is False
    assert result.evidence is None


def test_evidence_redacts_common_secret_shapes() -> None:
    result = classify_failure(
        "##[error]No server is currently available to service your request. "
        "Authorization: Bearer secret-token-value ghp_1234567890abcdef sk-abcdefghijk"
    )

    assert result.evidence is not None
    assert "secret-token-value" not in result.evidence
    assert "ghp_1234567890abcdef" not in result.evidence
    assert "sk-abcdefghijk" not in result.evidence
    assert "[REDACTED]" in result.evidence
