from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    rule_id: str
    classification: str
    confidence: str
    retry_recommended: bool
    patterns: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class ClassificationResult:
    classification: str
    confidence: str
    decision: str
    retry_recommended: bool
    rule_id: str | None
    evidence: str | None
    workflow_url: str | None = None
    job_id: str | None = None


RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="github-service-unavailable",
        classification="external_service_failure",
        confidence="high",
        retry_recommended=True,
        patterns=(
            re.compile(r"no server is currently available to service your request", re.I),
            re.compile(r"github.*(?:502|503|service unavailable)", re.I),
            re.compile(r"(?:502|503).*github", re.I),
        ),
    ),
    Rule(
        rule_id="workflow-configuration",
        classification="repository_configuration_failure",
        confidence="high",
        retry_recommended=False,
        patterns=(
            re.compile(r"invalid workflow file", re.I),
            re.compile(r"the workflow is not valid", re.I),
            re.compile(r"resource not accessible by integration", re.I),
            re.compile(r"branch protection.*(?:reject|require|violation)", re.I),
        ),
    ),
    Rule(
        rule_id="dependency-install",
        classification="dependency_or_install_failure",
        confidence="medium",
        retry_recommended=False,
        patterns=(
            re.compile(r"ERR_PNPM_(?:LOCKFILE|FETCH|PEER|OUTDATED|META_FETCH|NO_MATCHING_VERSION)", re.I),
            re.compile(r"could not resolve dependency", re.I),
            re.compile(r"resolutionimpossible", re.I),
            re.compile(r"no matching distribution found", re.I),
            re.compile(r"failed to (?:install|resolve) (?:package|dependency|dependencies)", re.I),
        ),
    ),
    Rule(
        rule_id="code-or-test",
        classification="code_or_test_failure",
        confidence="medium",
        retry_recommended=False,
        patterns=(
            re.compile(r"(?:^|\s)FAILED(?:\s|$)", re.I),
            re.compile(r"assertionerror", re.I),
            re.compile(r"(?:syntax|type|name|attribute)error:", re.I),
            re.compile(r"error TS\d+:", re.I),
            re.compile(r"tests? failed", re.I),
        ),
    ),
)

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[^\s]+"), r"\1[REDACTED]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{8,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_API_KEY]"),
)


def _sanitize(text: str) -> str:
    sanitized = text.strip()
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized[:500]


def _iter_lines(log_text: str) -> Iterable[str]:
    for line in log_text.splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped


def classify_failure(
    log_text: str,
    *,
    workflow_url: str | None = None,
    job_id: str | None = None,
) -> ClassificationResult:
    lines = tuple(_iter_lines(log_text))

    # Specific infrastructure failures intentionally outrank generic test/error text.
    for rule in RULES:
        for line in lines:
            if any(pattern.search(line) for pattern in rule.patterns):
                return ClassificationResult(
                    classification=rule.classification,
                    confidence=rule.confidence,
                    decision="needs_review",
                    retry_recommended=rule.retry_recommended,
                    rule_id=rule.rule_id,
                    evidence=_sanitize(line),
                    workflow_url=workflow_url,
                    job_id=job_id,
                )

    return ClassificationResult(
        classification="inconclusive",
        confidence="low",
        decision="needs_review",
        retry_recommended=False,
        rule_id=None,
        evidence=None,
        workflow_url=workflow_url,
        job_id=job_id,
    )


def _read_log(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Classify a CI job log into a small fail-closed set of maintainer categories. "
            "The result never marks a pull request safe to merge."
        )
    )
    parser.add_argument("log", help="Path to a decoded CI log, or '-' for stdin")
    parser.add_argument("--workflow-url", default=None)
    parser.add_argument("--job-id", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        log_text = _read_log(args.log)
    except OSError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    result = classify_failure(
        log_text,
        workflow_url=args.workflow_url,
        job_id=args.job_id,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
