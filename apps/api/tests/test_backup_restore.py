from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import stat
import zipfile
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


def test_backup_refuses_output_inside_data_and_symlinked_source(tmp_path):
    backup = _script_module("backup")
    data = tmp_path / "data"
    data.mkdir()
    (data / "record.txt").write_text("private record", encoding="utf-8")
    with pytest.raises(SystemExit, match="outside the data directory"):
        backup.build_backup(data, data / "backups")

    outside = tmp_path / "outside-secret.txt"
    outside.write_text("must not be followed", encoding="utf-8")
    try:
        (data / "linked-secret.txt").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are unavailable on this runner")
    with pytest.raises(SystemExit, match="symlink"):
        backup.build_backup(data, tmp_path / "backups")


def test_backup_restore_preserves_workspace_records_wal_commits_and_private_files(tmp_path):
    from personal_ai_os.db import Database

    backup = _script_module("backup")
    restore = _script_module("restore")
    data = tmp_path / "data"
    database_path = data / "personal_ai_os.db"
    database = Database(database_path)
    database.migrate()
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO user_projects(tenant_id, id, name, description, created_at) "
            "VALUES ('local', 'project-1', 'Private project', 'Preserve this project', '2026-01-01T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO conversations(id, title, provider, model, project_id, created_at, updated_at, tenant_id) "
            "VALUES ('conversation-1', 'Private conversation', 'openai', 'model-1', 'project-1', "
            "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'local')"
        )
        connection.execute(
            "INSERT INTO messages(id, conversation_id, role, content, tool_refs_json, created_at) "
            "VALUES ('message-1', 'conversation-1', 'user', 'private message', '[]', '2026-01-01T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO memories(id, type, text, source, confidence, valid_from, status, project_id, "
            "created_at, updated_at, tenant_id) VALUES ('memory-1', 'preference', 'private memory', "
            "'user', 1.0, NULL, 'active', 'project-1', '2026-01-01T00:00:00Z', "
            "'2026-01-01T00:00:00Z', 'local')"
        )
        connection.execute(
            "INSERT INTO repository_events(id, event_type, summary, artifact_id, project_id, details_json, "
            "created_at, tenant_id) VALUES ('event-1', 'outcome.recorded', 'private outcome', NULL, "
            "'project-1', '{}', '2026-01-01T00:00:00Z', 'local')"
        )

    attachment = data / "attachments" / "project-1" / "private-note.md"
    attachment.parent.mkdir(parents=True)
    attachment.write_text("private attachment body", encoding="utf-8")
    empty_directory = data / "empty-workspace" / "nested"
    empty_directory.mkdir(parents=True)

    wal_connection = sqlite3.connect(database_path)
    try:
        wal_connection.execute("PRAGMA journal_mode=WAL")
        wal_connection.execute("CREATE TABLE wal_probe (id INTEGER PRIMARY KEY, body TEXT NOT NULL)")
        wal_connection.execute("INSERT INTO wal_probe(body) VALUES ('committed WAL record')")
        wal_connection.commit()
        assert Path(f"{database_path}-wal").exists()
        archive = backup.build_backup(data, tmp_path / "backups")
    finally:
        wal_connection.close()

    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        manifest = json.loads(bundle.read("manifest.json"))
        assert "data/personal_ai_os.db" in names
        assert "data/attachments/project-1/private-note.md" in names
        assert not any(name.endswith(("-wal", "-shm", "-journal")) for name in names)
        assert {item["path"] for item in manifest["files"]} == {
            "personal_ai_os.db",
            "attachments/project-1/private-note.md",
        }
        database_record = next(item for item in manifest["files"] if item["path"] == "personal_ai_os.db")
        assert database_record["sha256"] == hashlib.sha256(bundle.read("data/personal_ai_os.db")).hexdigest()

    target = tmp_path / "new-parent" / "restored-data"
    assert restore.restore(archive, target) is None
    restored = Database(target / "personal_ai_os.db")
    with restored.connect() as connection:
        assert connection.execute("SELECT name FROM user_projects WHERE id='project-1'").fetchone()["name"] == "Private project"
        assert connection.execute("SELECT content FROM messages WHERE id='message-1'").fetchone()["content"] == "private message"
        assert connection.execute("SELECT text FROM memories WHERE id='memory-1'").fetchone()["text"] == "private memory"
        assert connection.execute("SELECT summary FROM repository_events WHERE id='event-1'").fetchone()["summary"] == "private outcome"
        assert connection.execute("SELECT body FROM wal_probe WHERE id=1").fetchone()["body"] == "committed WAL record"
    assert (target / "attachments/project-1/private-note.md").read_text(encoding="utf-8") == "private attachment body"
    assert (target / "empty-workspace/nested").is_dir()
    assert list((target / "empty-workspace/nested").iterdir()) == []


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "../escaped.txt",
        "..\\\\escaped.txt",
        "/absolute/escaped.txt",
        "C:/escaped.txt",
        "\\\\\\server\\\\share\\\\escaped.txt",
        "data/CON.txt",
        "data/trailing.",
        "data/illegal?.txt",
    ],
)
def test_restore_rejects_cross_platform_path_traversal_before_replacing_data(tmp_path, unsafe_name):
    restore = _script_module("restore")
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps({"format": "personal-ai-os-data-backup-v1"}))
        bundle.writestr("data/record.txt", "untrusted")
        bundle.writestr(unsafe_name, "escape attempt")
    target = tmp_path / "existing-data"
    target.mkdir()
    sentinel = target / "must-survive.txt"
    sentinel.write_text("existing private data", encoding="utf-8")

    with pytest.raises(SystemExit, match="unsafe path"):
        restore.restore(archive, target)

    assert sentinel.read_text(encoding="utf-8") == "existing private data"
    assert not (tmp_path / "escaped.txt").exists()


def test_restore_rejects_case_colliding_archive_paths_before_replacing_data(tmp_path):
    restore = _script_module("restore")
    archive = tmp_path / "case-collision.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps({"format": "personal-ai-os-data-backup-v1"}))
        bundle.writestr("data/Record.txt", "first")
        bundle.writestr("data/record.txt", "second")
    target = tmp_path / "existing-data"
    target.mkdir()
    sentinel = target / "must-survive.txt"
    sentinel.write_text("existing private data", encoding="utf-8")
    with pytest.raises(SystemExit, match="duplicate or case-colliding"):
        restore.restore(archive, target)
    assert sentinel.read_text(encoding="utf-8") == "existing private data"


def test_restore_rejects_zip_symlink_entries_before_replacing_data(tmp_path):
    restore = _script_module("restore")
    archive = tmp_path / "symlink.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps({"format": "personal-ai-os-data-backup-v1"}))
        bundle.writestr("data/record.txt", "safe")
        link = zipfile.ZipInfo("data/external-link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(link, "outside-target")

    target = tmp_path / "existing-data"
    target.mkdir()
    sentinel = target / "must-survive.txt"
    sentinel.write_text("existing private data", encoding="utf-8")
    with pytest.raises(SystemExit, match="link"):
        restore.restore(archive, target)
    assert sentinel.read_text(encoding="utf-8") == "existing private data"


def test_restore_detects_sha256_tampering_even_when_zip_crc_is_valid(tmp_path):
    backup = _script_module("backup")
    restore = _script_module("restore")
    data = tmp_path / "data"
    data.mkdir()
    (data / "private.txt").write_text("original private content", encoding="utf-8")
    original = backup.build_backup(data, tmp_path / "backups")
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(tampered, "w") as target_zip:
        for member in source.infolist():
            payload = b"modified content" if member.filename == "data/private.txt" else source.read(member)
            target_zip.writestr(member, payload)

    target = tmp_path / "existing-data"
    target.mkdir()
    sentinel = target / "must-survive.txt"
    sentinel.write_text("existing private data", encoding="utf-8")
    with pytest.raises(SystemExit, match="integrity check failed"):
        restore.restore(tampered, target)
    assert sentinel.read_text(encoding="utf-8") == "existing private data"


def test_restore_copy_failure_rolls_back_to_the_previous_data_directory(tmp_path, monkeypatch):
    backup = _script_module("backup")
    restore = _script_module("restore")
    data = tmp_path / "source-data"
    data.mkdir()
    (data / "new.txt").write_text("new snapshot", encoding="utf-8")
    archive = backup.build_backup(data, tmp_path / "backups")

    target = tmp_path / "target-data"
    target.mkdir()
    (target / "old.txt").write_text("previous snapshot", encoding="utf-8")

    def fail_after_partial_copy(source, destination):
        Path(destination).mkdir(parents=True)
        (Path(destination) / "partial.txt").write_text("partial", encoding="utf-8")
        raise OSError("simulated disk full during restore")

    monkeypatch.setattr(restore.shutil, "copytree", fail_after_partial_copy)
    with pytest.raises(OSError, match="disk full"):
        restore.restore(archive, target)
    assert (target / "old.txt").read_text(encoding="utf-8") == "previous snapshot"
    assert not (target / "partial.txt").exists()
    assert not list(tmp_path.glob("target-data.before-restore-*"))


def test_legacy_v1_archive_without_sha256_file_list_remains_restorable(tmp_path):
    restore = _script_module("restore")
    archive = tmp_path / "legacy-v1.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps({"format": "personal-ai-os-data-backup-v1"}))
        bundle.writestr("data/legacy-record.txt", "legacy private record")
    target = tmp_path / "restored"
    assert restore.restore(archive, target) is None
    assert (target / "legacy-record.txt").read_text(encoding="utf-8") == "legacy private record"


@pytest.mark.parametrize("relative", ["manifest.json", "data", "data/nested.txt"])
def test_backup_round_trip_preserves_names_inside_data_root(tmp_path, relative):
    backup = _script_module("backup")
    restore = _script_module("restore")
    source = tmp_path / "source"
    fixture = source / relative
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text("synthetic fixture", encoding="utf-8")

    archive = backup.build_backup(source, tmp_path / "backups")
    target = tmp_path / "restored"
    assert restore.restore(archive, target) is None
    assert (target / relative).read_text(encoding="utf-8") == "synthetic fixture"


def test_backup_rejects_case_colliding_directories_before_creating_archive(tmp_path):
    backup = _script_module("backup")
    source = tmp_path / "source"
    (source / "Notes").mkdir(parents=True)
    if (source / "notes").exists():
        pytest.skip("Source filesystem is case-insensitive")
    (source / "notes").mkdir()
    (source / "Notes" / "first.txt").write_text("first", encoding="utf-8")
    (source / "notes" / "second.txt").write_text("second", encoding="utf-8")
    output = tmp_path / "backups"

    with pytest.raises(SystemExit, match="case-colliding"):
        backup.build_backup(source, output)

    assert not list(output.glob("*.zip"))
    assert (source / "Notes" / "first.txt").read_text(encoding="utf-8") == "first"
    assert (source / "notes" / "second.txt").read_text(encoding="utf-8") == "second"


@pytest.mark.parametrize(
    "members",
    [
        ("data/Notes/first.txt", "data/notes/second.txt"),
        ("data/Notes", "data/Notes/second.txt"),
        ("data/Notes/first.txt", "data/Notes"),
    ],
)
def test_restore_rejects_conflicting_implicit_parents_before_replacing_data(tmp_path, members):
    restore = _script_module("restore")
    archive = tmp_path / "conflict.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps({"format": "personal-ai-os-data-backup-v1"}))
        for member in members:
            bundle.writestr(member, "synthetic fixture")
    target = tmp_path / "existing-data"
    target.mkdir()
    sentinel = target / "must-survive.txt"
    sentinel.write_text("existing data", encoding="utf-8")

    with pytest.raises(SystemExit, match="case-colliding|file/directory conflict"):
        restore.restore(archive, target)

    assert sentinel.read_text(encoding="utf-8") == "existing data"
    assert list(target.iterdir()) == [sentinel]
