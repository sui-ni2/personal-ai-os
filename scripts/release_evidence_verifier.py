from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any


REQUIRED_CHECKS: tuple[str, ...] = (
    "CI",
    "CodeQL",
    "Dependency Review",
    "Platform Readiness",
    "Release provider smoke",
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.I)


@dataclass(frozen=True)
class Blocker:
    code: str
    check: str | None
    detail: str


@dataclass(frozen=True)
class VerificationResult:
    ready_to_tag: bool
    decision: str
    expected_sha: str
    as_of: str
    max_age_hours: float
    required_checks: tuple[str, ...]
    blockers: tuple[Blocker, ...]


def _parse_time(value: str, *, field: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_release_evidence(
    payload: dict[str, Any],
    *,
    expected_sha: str,
    as_of: datetime,
    max_age_hours: float = 48.0,
) -> VerificationResult:
    if not _SHA_RE.fullmatch(expected_sha):
        raise ValueError("expected_sha must be a full 40-character hexadecimal commit SHA")
    if as_of.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be positive")

    as_of_utc = as_of.astimezone(timezone.utc)
    max_age = timedelta(hours=max_age_hours)
    blockers: list[Blocker] = []

    declared_sha = payload.get("commit_sha")
    if declared_sha != expected_sha:
        blockers.append(
            Blocker(
                code="bundle_commit_mismatch",
                check=None,
                detail=f"bundle commit_sha is {declared_sha!r}, expected {expected_sha}",
            )
        )

    checks = payload.get("checks")
    if not isinstance(checks, list):
        checks = []
        blockers.append(
            Blocker(
                code="invalid_checks",
                check=None,
                detail="checks must be a list",
            )
        )

    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in checks:
        if not isinstance(item, dict):
            blockers.append(
                Blocker(
                    code="invalid_check_entry",
                    check=None,
                    detail="every checks entry must be an object",
                )
            )
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            blockers.append(
                Blocker(
                    code="invalid_check_name",
                    check=None,
                    detail="every check must have a non-empty name",
                )
            )
            continue
        by_name.setdefault(name, []).append(item)

    for name in REQUIRED_CHECKS:
        entries = by_name.get(name, [])
        if not entries:
            blockers.append(
                Blocker(code="missing_check", check=name, detail="required check is missing")
            )
            continue
        if len(entries) != 1:
            blockers.append(
                Blocker(
                    code="duplicate_check",
                    check=name,
                    detail=f"required check appears {len(entries)} times",
                )
            )
            continue

        entry = entries[0]
        conclusion = entry.get("conclusion")
        if conclusion != "success":
            blockers.append(
                Blocker(
                    code="check_not_successful",
                    check=name,
                    detail=f"conclusion is {conclusion!r}, expected 'success'",
                )
            )

        head_sha = entry.get("head_sha")
        if head_sha != expected_sha:
            blockers.append(
                Blocker(
                    code="check_commit_mismatch",
                    check=name,
                    detail=f"head_sha is {head_sha!r}, expected {expected_sha}",
                )
            )

        source_url = entry.get("url")
        if not isinstance(source_url, str) or not source_url.startswith("https://"):
            blockers.append(
                Blocker(
                    code="missing_source_url",
                    check=name,
                    detail="an HTTPS source URL is required for auditability",
                )
            )

        completed_at_raw = entry.get("completed_at")
        if not isinstance(completed_at_raw, str):
            blockers.append(
                Blocker(
                    code="missing_completed_at",
                    check=name,
                    detail="completed_at is required",
                )
            )
            continue

        try:
            completed_at = _parse_time(completed_at_raw, field=f"{name}.completed_at")
        except ValueError as exc:
            blockers.append(
                Blocker(code="invalid_completed_at", check=name, detail=str(exc))
            )
            continue

        if completed_at > as_of_utc:
            blockers.append(
                Blocker(
                    code="future_check",
                    check=name,
                    detail=f"completed_at {_iso(completed_at)} is after as_of {_iso(as_of_utc)}",
                )
            )
        elif as_of_utc - completed_at > max_age:
            blockers.append(
                Blocker(
                    code="stale_check",
                    check=name,
                    detail=(
                        f"completed_at {_iso(completed_at)} is older than "
                        f"{max_age_hours:g} hours at {_iso(as_of_utc)}"
                    ),
                )
            )

    result_blockers = tuple(blockers)
    return VerificationResult(
        ready_to_tag=not result_blockers,
        decision="ready_to_tag" if not result_blockers else "blocked",
        expected_sha=expected_sha,
        as_of=_iso(as_of_utc),
        max_age_hours=max_age_hours,
        required_checks=REQUIRED_CHECKS,
        blockers=result_blockers,
    )


def _read_payload(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("evidence payload must be a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a release evidence bundle without creating a tag or release. "
            "Missing, stale, non-successful, or wrong-commit evidence blocks readiness."
        )
    )
    parser.add_argument("evidence", help="Evidence JSON path, or '-' for stdin")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--as-of", default=None, help="ISO-8601 time; defaults to current UTC")
    parser.add_argument("--max-age-hours", type=float, default=48.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = _read_payload(args.evidence)
        as_of = (
            _parse_time(args.as_of, field="as_of")
            if args.as_of
            else datetime.now(timezone.utc)
        )
        result = verify_release_evidence(
            payload,
            expected_sha=args.expected_sha,
            as_of=as_of,
            max_age_hours=args.max_age_hours,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0 if result.ready_to_tag else 1


if __name__ == "__main__":
    raise SystemExit(main())
