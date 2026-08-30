from __future__ import annotations

import pytest

from scripts.tester_feedback_traceability import trace_tester_feedback


def test_trace_requires_real_urls_and_never_claims_adoption() -> None:
    result = trace_tester_feedback(
        {
            "report_url": "https://github.com/example/repo/issues/7",
            "triage_url": "https://github.com/example/repo/issues/7#triage",
            "reproduction_url": "https://github.com/example/repo/issues/8",
            "fix_pr_url": "https://github.com/example/repo/pull/9",
            "external_retest_url": "https://github.com/example/repo/issues/7#retest",
        }
    )

    assert result.state == "external_retest_recorded"
    assert result.missing_steps == ()
    assert result.adoption_evidence is False
    assert result.ledger_eligible is False


def test_trace_exposes_missing_steps_without_inference() -> None:
    result = trace_tester_feedback({"report_url": "https://github.com/example/repo/issues/7"})

    assert result.state == "report_received"
    assert result.missing_steps == ("triage", "reproduction", "fix_pr", "external_retest")


def test_trace_rejects_non_https_references() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        trace_tester_feedback({"report_url": "http://example.test/issues/7"})
