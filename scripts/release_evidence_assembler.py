from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from scripts.release_evidence_verifier import REQUIRED_CHECKS


def _full_sha(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value.lower()):
        raise ValueError(f"{field} must be a full 40-character hexadecimal commit SHA")
    return value


def assemble_release_evidence(source: dict[str, Any], *, expected_sha: str) -> dict[str, Any]:
    """Normalize supplied GitHub check metadata; verifier remains the release authority."""

    expected_sha = _full_sha(expected_sha, field="expected_sha")
    checks = source.get("checks")
    if not isinstance(checks, list):
        raise ValueError("source.checks must be a list")
    assembled: list[dict[str, Any]] = []
    for item in checks:
        if not isinstance(item, dict) or item.get("name") not in REQUIRED_CHECKS:
            continue
        url = item.get("url", item.get("details_url"))
        assembled.append(
            {
                "name": item.get("name"),
                "conclusion": item.get("conclusion"),
                "head_sha": item.get("head_sha"),
                "completed_at": item.get("completed_at"),
                "url": url,
            }
        )
    return {"commit_sha": expected_sha, "checks": assembled}


def _read_payload(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("source evidence must be a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize supplied release-check metadata. It does not infer checks or approve a release."
    )
    parser.add_argument("source", help="Source checks JSON path, or '-' for stdin")
    parser.add_argument("--expected-sha", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = assemble_release_evidence(
            _read_payload(args.source), expected_sha=args.expected_sha
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
