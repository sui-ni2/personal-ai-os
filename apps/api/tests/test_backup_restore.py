from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


def _script_module(name: str):
    path = Path(__file__).parents[3] / "scripts" / f"{name}-data.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_backups_created_at_the_same_time_preserve_both_snapshots(tmp_path, monkeypatch):
    backup = _script_module("backup")
    restore = _script_module("restore")
    monkeypatch.setattr(backup, "datetime", FixedClock)
    data = tmp_path / "data"
    data.mkdir()
    source = data / "fixture.txt"
    source.write_text("first snapshot", encoding="utf-8")
    first = backup.build_backup(data, tmp_path / "backups")
    first_bytes = first.read_bytes()

    source.write_text("second snapshot", encoding="utf-8")
    second = backup.build_backup(data, tmp_path / "backups")

    assert first != second
    assert first.read_bytes() == first_bytes
    assert len(list((tmp_path / "backups").glob("*.zip"))) == 2
    for archive, expected, target in (
        (first, "first snapshot", tmp_path / "restore-first"),
        (second, "second snapshot", tmp_path / "restore-second"),
    ):
        assert restore.restore(archive, target) is None
        assert (target / "fixture.txt").read_text(encoding="utf-8") == expected


def test_archive_name_collision_cannot_overwrite_an_existing_backup(tmp_path, monkeypatch):
    backup = _script_module("backup")
    monkeypatch.setattr(backup, "datetime", FixedClock)
    monkeypatch.setattr(backup, "uuid4", lambda: SimpleNamespace(hex="fixed-collision"), raising=False)
    data = tmp_path / "data"
    data.mkdir()
    source = data / "fixture.txt"
    source.write_text("preserved snapshot", encoding="utf-8")
    first = backup.build_backup(data, tmp_path / "backups")
    first_bytes = first.read_bytes()

    source.write_text("later state", encoding="utf-8")
    with pytest.raises(FileExistsError):
        backup.build_backup(data, tmp_path / "backups")

    assert first.read_bytes() == first_bytes
    assert len(list((tmp_path / "backups").glob("*.zip"))) == 1


def test_empty_data_directory_backup_restores_without_losing_prior_data(tmp_path):
    backup = _script_module("backup")
    restore = _script_module("restore")
    empty = tmp_path / "empty-data"
    empty.mkdir()
    archive = backup.build_backup(empty, tmp_path / "backups")
    target = tmp_path / "restored"
    target.mkdir()
    (target / "fixture.txt").write_text("previous state", encoding="utf-8")

    prior = restore.restore(archive, target)

    assert target.is_dir()
    assert list(target.iterdir()) == []
    assert prior is not None
    assert (prior / "fixture.txt").read_text(encoding="utf-8") == "previous state"
