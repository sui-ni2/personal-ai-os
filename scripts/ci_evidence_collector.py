from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any

from scripts.ci_failure_classifier import ClassificationResult, classify_failure


@dataclass(frozen=True)
class CIEvidence:
    workflow_name: str
    workflow_url: str
    job_id: str | None
    head_sha: str
    conclusion: str
    completed_at: str
    failure_classification: ClassificationResult | None
    maintainer_decision: str


def _required_string(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"metadata.{key} must be a non-empty string")
    return value.strip()


def collect_ci_evidence(metadata: dict[str, Any], log_text: str) -> CIEvidence:
    """Collect bounded redacted CI evidence without deciding that a change is safe to merge."""

    workflow_url = _required_string(metadata, "workflow_url")
    if not workflow_url.startswith("https://"):
        raise ValueError("metadata.workflow_url must be HTTPS")
    conclusion = _required_string(metadata, "conclusion")
    job_id = metadata.get("job_id")
    if job_id is not None and not isinstance(job_id, str):
        raise ValueError("metadata.job_id must be a string when supplied")
    classification = (
        None
        if conclusion == "success"
        else classify_failure(log_text, workflow_url=workflow_url, job_id=job_id)
    )
    return CIEvidence(
        workflow_name=_required_string(metadata, "workflow_name"),
        workflow_url=workflow_url,
        job_id=job_id,
        head_sha=_required_string(metadata, "head_sha"),
        conclusion=conclusion,
        completed_at=_required_string(metadata, "completed_at"),
        failure_classification=classification,
        maintainer_decision="needs_review",
    )


def _read_json(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object")
    return value


def _read_log(path: str | None) -> str:
    if path is None:
        return ""
    return sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect redacted CI metadata and deterministic failure classification for maintainer review."
    )
    parser.add_argument("metadata", help="CI metadata JSON path, or '-' for stdin")
    parser.add_argument("--log", default=None, help="Optional decoded log path. Never pass a secret-bearing raw log.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.metadata == "-" and args.log == "-":
        print(json.dumps({"error": "metadata and log cannot both read stdin"}), file=sys.stderr)
        return 2
    try:
        result = collect_ci_evidence(_read_json(args.metadata), _read_log(args.log))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
