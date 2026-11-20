from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "check_project_delivery_register.py"
SPEC = importlib.util.spec_from_file_location("delivery_register_check", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def _sample():
    data = json.loads((ROOT / "docs/project-delivery-register.json").read_text(encoding="utf-8"))
    return data


def test_committed_delivery_register_has_no_missing_or_duplicate_workstreams() -> None:
    document = _sample()
    index = (ROOT / "docs/project-delivery-register.md").read_text(encoding="utf-8")
    assert checker.validate_register(document, ROOT) == []
    assert checker.validate_index(document, index) == []
    baseline = (ROOT / "docs/project-delivery-ids.txt").read_text(encoding="utf-8")
    assert checker.validate_id_baseline(document, baseline) == []
    assert len({item["id"] for item in document["items"]}) == len(document["items"])


def test_duplicated_workstream_cannot_silently_pass() -> None:
    data = _sample()
    data["items"].append(copy.deepcopy(data["items"][0]))
    assert any("duplicate" in error for error in checker.validate_register(data, ROOT))


def test_completion_without_proof_is_rejected() -> None:
    data = _sample()
    item = next(row for row in data["items"] if row["lane"] == "completed")
    item.pop("proof_ref")
    assert any("completed lane requires proof_ref" in e for e in checker.validate_register(data, ROOT))


def test_implementation_ready_requires_an_existing_design() -> None:
    data = _sample()
    item = next(row for row in data["items"] if row["lane"] == "ready")
    item["design_ref"] = "docs/this-design-does-not-exist.md"
    assert any("design_ref" in e for e in checker.validate_register(data, ROOT))


def test_external_and_deferred_work_cannot_lose_review_gates() -> None:
    data = _sample()
    external = next(row for row in data["items"] if row["lane"] == "external")
    deferred = next(row for row in data["items"] if row["lane"] == "deferred")
    external["proof_needed"] = ""
    deferred["review_trigger"] = ""
    errors = checker.validate_register(data, ROOT)
    assert any("proof_needed" in e for e in errors)
    assert any("review_trigger" in e for e in errors)


def test_index_detects_hidden_workstream_omission() -> None:
    data = _sample()
    index = (ROOT / "docs/project-delivery-register.md").read_text(encoding="utf-8")
    index = "\n".join(
        line for line in index.splitlines() if not line.startswith("| PAI-004 |")
    )
    assert any("missing IDs PAI-004" in e for e in checker.validate_index(data, index))


def test_index_rejects_paper_promotion_without_register_update() -> None:
    data = _sample()
    index = (ROOT / "docs/project-delivery-register.md").read_text(encoding="utf-8")
    item = next(row for row in data["items"] if row["id"] == "PAI-012")
    item["lane"] = "completed"
    assert any("wrong lane" in e for e in checker.validate_index(data, index))


def test_unknown_lane_and_unsafe_paths_fail_closed() -> None:
    data = _sample()
    row = data["items"][0]
    row["lane"] = "ready_to_claim_success"
    row["source_refs"] = ["../private/notes.md"]
    errors = checker.validate_register(data, ROOT)
    assert any("unknown lane" in e for e in errors)
    assert any("source reference" in e for e in errors)


def test_synchronized_json_index_deletion_still_fails_historical_baseline() -> None:
    data = _sample()
    index = (ROOT / "docs/project-delivery-register.md").read_text(encoding="utf-8")
    baseline = (ROOT / "docs/project-delivery-ids.txt").read_text(encoding="utf-8")
    data["items"] = [item for item in data["items"] if item["id"] != "PAI-004"]
    index = "\n".join(
        line for line in index.splitlines() if not line.startswith("| PAI-004 |")
    )
    assert checker.validate_index(data, index) == []
    assert any("removed commitments PAI-004" in error
               for error in checker.validate_id_baseline(data, baseline))


def test_new_plan_id_requires_explicit_history_append() -> None:
    data = _sample()
    baseline = (ROOT / "docs/project-delivery-ids.txt").read_text(encoding="utf-8")
    item = copy.deepcopy(data["items"][0])
    item["id"] = "PAI-099"
    data["items"].append(item)
    assert any("new IDs require" in error
               for error in checker.validate_id_baseline(data, baseline))
