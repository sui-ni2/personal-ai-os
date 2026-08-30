from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any


_URL_FIELDS = ("report_url", "triage_url", "reproduction_url", "fix_pr_url", "external_retest_url")


@dataclass(frozen=True)
class TesterFeedbackTrace:
    report_url: str
    triage_url: str | None
    reproduction_url: str | None
    fix_pr_url: str | None
    external_retest_url: str | None
    state: str
    missing_steps: tuple[str, ...]
    adoption_evidence: bool
    ledger_eligible: bool
    maintainer_decision: str


def _url(value: Any, *, field: str, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.startswith("https://"):
        raise ValueError(f"{field} must be an HTTPS URL")
    return value


def trace_tester_feedback(payload: dict[str, Any]) -> TesterFeedbackTrace:
    values = {field: _url(payload.get(field), field=field, required=field == "report_url") for field in _URL_FIELDS}
    missing: list[str] = []
    if values["triage_url"] is None:
        missing.append("triage")
    if values["reproduction_url"] is None:
        missing.append("reproduction")
    if values["fix_pr_url"] is None:
        missing.append("fix_pr")
    if values["external_retest_url"] is None:
        missing.append("external_retest")
    if not missing:
        state = "external_retest_recorded"
    elif values["fix_pr_url"] is not None:
        state = "fix_pending_external_retest"
    elif values["triage_url"] is not None:
        state = "triaged_pending_reproduction"
    else:
        state = "report_received"
    return TesterFeedbackTrace(
        report_url=values["report_url"] or "",
        triage_url=values["triage_url"],
        reproduction_url=values["reproduction_url"],
        fix_pr_url=values["fix_pr_url"],
        external_retest_url=values["external_retest_url"],
        state=state,
        missing_steps=tuple(missing),
        adoption_evidence=False,
        ledger_eligible=False,
        maintainer_decision="needs_review",
    )


def _read_payload(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("trace payload must be a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Track real tester feedback through review without converting it into adoption evidence."
    )
    parser.add_argument("trace", help="Trace JSON path, or '-' for stdin")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = trace_tester_feedback(_read_payload(args.trace))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
