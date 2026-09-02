import importlib.util
import json
from pathlib import Path

from personal_ai_os.config import (
    CANONICAL_DATABASE_FILENAME,
    LEGACY_DATABASE_FILENAMES,
    Settings,
)
from personal_ai_os.db import Database, MIGRATIONS


def _script_module(filename: str, name: str):
    path = Path(__file__).parents[3] / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _doctor_module():
    return _script_module("doctor.py", "personal_ai_os_doctor")


def _migrated_database(data_dir: Path) -> Database:
    settings = Settings(
        data_dir=data_dir,
        cors_origins=("http://localhost:3000",),
        openai_models=("openai-test",),
        anthropic_models=("anthropic-test",),
        default_provider="openai",
        default_model="openai-test",
    )
    database = Database(settings.database_path)
    database.migrate()
    return database


def test_doctor_report_is_safe_to_share_and_excludes_secret_values(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    install_dir = tmp_path / "install"
    (install_dir / "backups").mkdir(parents=True)
    (install_dir / "backups" / "backup.zip").write_bytes(b"fixture")
    (install_dir / "update-state.json").write_text(json.dumps({"status": "UPDATED", "token": "secret-value-must-not-appear"}), encoding="utf-8")
    for name in [
        "PERSONAL_AI_OS_OPENAI_API_KEY",
        "PERSONAL_AI_OS_ANTHROPIC_API_KEY",
        "PERSONAL_AI_OS_MCP_STDIO_COMMANDS",
    ]:
        monkeypatch.setenv(name, "secret-value-must-not-appear")
    report = _doctor_module().collect_report(data_dir, install_dir)
    encoded = str(report)
    assert report["safe_to_share"] is True
    assert report["providers"]["configured"]["openai"] is True
    assert report["runtime"]["application_version"]
    assert report["data_directory"]["location"] == "configured_local_path_redacted"
    assert report["backups"] == {"directory_present": True, "archive_count": 1, "archive_names_exposed": False}
    assert report["update"] == {"metadata_present": True, "status": "UPDATED"}
    assert "secret-value-must-not-appear" not in encoded


def test_doctor_redacts_malformed_update_metadata(tmp_path: Path) -> None:
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    (install_dir / "update-state.json").write_text('{"status":"private conversation text"}', encoding="utf-8")
    report = _doctor_module().collect_report(tmp_path / "data", install_dir)
    assert report["update"] == {"metadata_present": True, "status": "UNAVAILABLE_OR_REDACTED"}


def test_doctor_uses_the_canonical_runtime_database_path_and_migration_version(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    database = _migrated_database(data_dir)

    report = _doctor_module().collect_report(data_dir)

    assert database.path == data_dir / CANONICAL_DATABASE_FILENAME
    assert database.path.is_file()
    assert report["database"] == {
        "status": "ok",
        "integrity": "ok",
        "migration_version": max(version for version, _ in MIGRATIONS),
        "location": "canonical",
    }


def test_doctor_reports_a_missing_canonical_database_without_guessing(tmp_path: Path) -> None:
    report = _doctor_module().collect_report(tmp_path / "missing")

    assert report["database"] == {
        "status": "missing",
        "integrity": "not_applicable",
        "migration_version": 0,
        "location": "canonical",
    }


def test_doctor_reads_but_never_moves_a_legacy_database_path(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    legacy_path = data_dir / LEGACY_DATABASE_FILENAMES[0]
    legacy_database = Database(legacy_path)
    legacy_database.migrate()

    report = _doctor_module().collect_report(data_dir)

    assert report["database"] == {
        "status": "legacy_detected",
        "integrity": "ok",
        "migration_version": max(version for version, _ in MIGRATIONS),
        "location": "legacy",
    }
    assert legacy_path.is_file()
    assert not (data_dir / CANONICAL_DATABASE_FILENAME).exists()


def test_backup_and_restore_preserve_the_canonical_database_path(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _migrated_database(data_dir)
    backup_module = _script_module("backup-data.py", "personal_ai_os_backup")
    restore_module = _script_module("restore-data.py", "personal_ai_os_restore")

    archive = backup_module.build_backup(data_dir, tmp_path / "backups")
    restored_dir = tmp_path / "restored-data"
    prior = restore_module.restore(archive, restored_dir)
    report = _doctor_module().collect_report(restored_dir)

    assert prior is None
    assert (restored_dir / CANONICAL_DATABASE_FILENAME).is_file()
    assert report["database"]["status"] == "ok"
    assert report["database"]["migration_version"] == max(version for version, _ in MIGRATIONS)
