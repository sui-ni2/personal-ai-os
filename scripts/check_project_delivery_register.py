#!/usr/bin/env python3
"""Fail-closed, network-free integrity check for the public product delivery register.

This checks bookkeeping only: source paths, lane gates and the human index. It
does NOT validate remote PR state, release evidence or independent adoption.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER = Path("docs/project-delivery-register.json")
INDEX = Path("docs/project-delivery-register.md")

LANES = ("active", "ready", "design", "external", "deferred", "completed")
GATE_BY_LANE = {
    "active": "work_ref",
    "ready": "design_ref",
    "design": "design_goal",
    "external": "proof_needed",
    "deferred": "review_trigger",
    "completed": "proof_ref",
}
LANE_BY_HEADING = {
    "1": "active",
    "2": "ready",
    "3": "design",
    "4": "external",
    "5": "deferred",
    "6": "completed",
}
ID_PATTERN = re.compile(r"^PAI-[0-9]{3}$")
TABLE_ROW = re.compile(r"^\|\s*(PAI-[0-9]{3})\s*\|")


def _is_nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _safe_reference(ref: str, root: Path) -> bool:
    if ref.startswith("https://github.com/"):
        return True
    if "://" in ref or ref.startswith("/") or "\\" in ref:
        return False
    parts = Path(ref).parts
    if ".." in parts or not parts:
        return False
    return (root / ref).is_file()


def validate_register(document: Any, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["register must be a JSON object"]
    if document.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if document.get("repository") != "sui-ni2/personal-ai-os":
        errors.append("repository must be the canonical personal-ai-os repo")
    if not _is_nonempty(document.get("snapshot_date")):
        errors.append("snapshot_date must be present")
    rows = document.get("items")
    if not isinstance(rows, list) or not rows:
        return errors + ["items must be a nonempty array"]

    seen: set[str] = set()
    for index, item in enumerate(rows):
        marker = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{marker}: entry must be an object")
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not ID_PATTERN.fullmatch(item_id):
            errors.append(f"{marker}: invalid public workstream ID")
            continue
        if item_id in seen:
            errors.append(f"{item_id}: duplicate ID")
        seen.add(item_id)
        lane = item.get("lane")
        if lane not in LANES:
            errors.append(f"{item_id}: unknown lane {lane!r}")
        if item.get("priority") not in ("P0", "P1", "P2", "P3"):
            errors.append(f"{item_id}: invalid priority")
        for field in ("title", "acceptance", "next_step"):
            if not _is_nonempty(item.get(field)):
                errors.append(f"{item_id}: missing {field}")
        refs = item.get("source_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{item_id}: source_refs must contain evidence paths")
        else:
            for ref in refs:
                if not _is_nonempty(ref) or not _safe_reference(ref, root):
                    errors.append(f"{item_id}: unsupported or missing source reference")
        gate = GATE_BY_LANE.get(lane)
        if gate and not _is_nonempty(item.get(gate)):
            errors.append(f"{item_id}: {lane} lane requires {gate}")
        if gate in ("work_ref", "design_ref", "proof_ref"):
            ref = item.get(gate)
            if _is_nonempty(ref) and not _safe_reference(ref, root):
                errors.append(f"{item_id}: {gate} is not a recognized public source")
    return errors


def validate_index(document: Any, markdown: str) -> list[str]:
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        return ["cannot validate index without a register"]
    items = {
        item["id"]: item
        for item in document["items"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    errors: list[str] = []
    seen: set[str] = set()
    lane: str | None = None
    for line in markdown.splitlines():
        heading = re.match(r"^### ([1-6]) · ", line)
        if heading:
            lane = LANE_BY_HEADING[heading.group(1)]
        match = TABLE_ROW.match(line)
        if not match:
            continue
        item_id = match.group(1)
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if item_id in seen:
            errors.append(f"index: duplicate {item_id}")
        seen.add(item_id)
        item = items.get(item_id)
        if item is None:
            errors.append(f"index: untracked {item_id}")
            continue
        if lane != item.get("lane"):
            errors.append(f"index: {item_id} is in the wrong lane")
        if len(cells) != 4 or cells[1] != item.get("priority"):
            errors.append(f"index: {item_id} priority or cell count differs")
        elif cells[2] != item.get("title") or cells[3] != item.get("next_step"):
            errors.append(f"index: {item_id} title/next_step differs from JSON")
    missing = set(items) - seen
    if missing:
        errors.append("index: missing IDs " + ", ".join(sorted(missing)))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        document = json.loads((root / REGISTER).read_text(encoding="utf-8"))
        markdown = (root / INDEX).read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"DELIVERY_REGISTER_BLOCKED: {type(exc).__name__}")
        return 1
    errors = validate_register(document, root) + validate_index(document, markdown)
    if errors:
        for error in errors:
            print(f"DELIVERY_REGISTER_BLOCKED: {error}")
        return 1
    print(f"DELIVERY_REGISTER_STRUCTURAL_PASS: {len(document['items'])} workstreams; remote and external evidence remain unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
