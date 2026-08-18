from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import re
from pathlib import Path
import sys
from typing import Iterable


@dataclass(frozen=True)
class TriageRule:
    rule_id: str
    category: str
    patterns: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class TriageResult:
    category: str
    confidence: str
    decision: str
    adoption_evidence: bool
    rule_id: str | None
    evidence: str | None
    needs_reproduction: bool
    needs_maintainer_review: bool
    privacy_redactions_applied: bool
    source_url: str | None = None


RULES: tuple[TriageRule, ...] = (
    TriageRule(
        rule_id="install-or-startup-friction",
        category="setup_friction",
        patterns=(
            re.compile(r"(?:install|setup|bootstrap|docker compose|fresh clone).*(?:fail|error|stuck|unclear|cannot|can't)", re.I),
            re.compile(r"(?:fail|error|stuck|unclear|cannot|can't).*(?:install|setup|bootstrap|docker compose|fresh clone)", re.I),
        ),
    ),
    TriageRule(
        rule_id="documentation-gap",
        category="documentation_gap",
        patterns=(
            re.compile(r"(?:docs?|readme|instruction|guide).*(?:wrong|missing|unclear|outdated|confusing)", re.I),
            re.compile(r"(?:wrong|missing|unclear|outdated|confusing).*(?:docs?|readme|instruction|guide)", re.I),
        ),
    ),
    TriageRule(
        rule_id="reproducible-product-bug",
        category="product_bug",
        patterns=(
            re.compile(r"(?:crash|traceback|500|exception|broken|does not work|doesn't work)", re.I),
            re.compile(r"(?:restart|persist|memory|chat|provider|mcp|project).*(?:lost|fails?|broken|error)", re.I),
        ),
    ),
    TriageRule(
        rule_id="feature-request",
        category="feature_request",
        patterns=(
            re.compile(r"(?:feature request|would be useful|please add|could you add|support for)", re.I),
        ),
    ),
    TriageRule(
        rule_id="positive-or-negative-use-outcome",
        category="use_outcome",
        patterns=(
            re.compile(r"(?:used|tried|tested|running|worked|stopped using|kept using).*(?:workflow|project|chat|memory|mcp|provider|ollama)", re.I),
            re.compile(r"(?:workflow|project|chat|memory|mcp|provider|ollama).*(?:worked|failed|useful|blocked|stopped)", re.I),
        ),
    ),
)

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[^\s]+"), r"\1[REDACTED]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{8,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)(?:OPENAI|ANTHROPIC|API)_KEY\s*=\s*[^\s]+"), "[REDACTED_ENV_SECRET]"),
)


def _sanitize(text: str) -> tuple[str, bool]:
    sanitized = text.strip()
    changed = False
    for pattern, replacement in _SECRET_PATTERNS:
        updated = pattern.sub(replacement, sanitized)
        if updated != sanitized:
            changed = True
            sanitized = updated
    return sanitized[:700], changed


def _lines(text: str) -> Iterable[str]:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped


def triage_feedback(text: str, *, source_url: str | None = None) -> TriageResult:
    if source_url is not None and not source_url.startswith("https://"):
        raise ValueError("source_url must be HTTPS when supplied")

    lines = tuple(_lines(text))
    for rule in RULES:
        for line in lines:
            if any(pattern.search(line) for pattern in rule.patterns):
                evidence, redacted = _sanitize(line)
                needs_reproduction = rule.category in ("setup_friction", "product_bug")
                return TriageResult(
                    category=rule.category,
                    confidence="medium",
                    decision="needs_review",
                    adoption_evidence=False,
                    rule_id=rule.rule_id,
                    evidence=evidence,
                    needs_reproduction=needs_reproduction,
                    needs_maintainer_review=True,
                    privacy_redactions_applied=redacted,
                    source_url=source_url,
                )

    _, redacted = _sanitize(text)
    return TriageResult(
        category="inconclusive",
        confidence="low",
        decision="needs_review",
        adoption_evidence=False,
        rule_id=None,
        evidence=None,
        needs_reproduction=False,
        needs_maintainer_review=True,
        privacy_redactions_applied=redacted,
        source_url=source_url,
    )


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Classify sanitized first-hand tester feedback for maintainer triage. "
            "The result never marks a report as verified adoption evidence."
        )
    )
    parser.add_argument("feedback", help="Feedback text path, or '-' for stdin")
    parser.add_argument("--source-url", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = _read_text(args.feedback)
        result = triage_feedback(text, source_url=args.source_url)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
