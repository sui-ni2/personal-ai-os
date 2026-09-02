from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from personal_ai_os.db import Database, MIGRATIONS, MigrationSafetyError, _statements


def _legacy_v5_database(path: Path) -> Database:
    database = Database(path)
    with database.connect() as connection:
        connection.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        for version, script in MIGRATIONS[:5]:
            for statement in _statements(script):
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (version, "2026-01-01T00:00:00+00:00"),
            )
        connection.execute(
            "INSERT INTO tenants(id, deployment_mode, created_at) VALUES ('local', 'community', '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO actors(id, created_at) VALUES ('local-owner', '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO tenant_memberships(tenant_id, actor_id, role, created_at) VALUES ('local', 'local-owner', 'owner', '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO user_projects(tenant_id, id, name, description, created_at) VALUES ('local', 'legacy-project', 'Legacy project', 'Preserve this project', '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO conversations(id, title, provider, model, project_id, created_at, updated_at, tenant_id) VALUES ('conversation-1', 'Legacy conversation', 'openai', 'legacy-model', 'legacy-project', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 'local')"
        )
        connection.execute(
            "INSERT INTO messages(id, conversation_id, role, content, tool_refs_json, created_at) VALUES ('message-1', 'conversation-1', 'user', 'legacy message', '[]', '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO memories(id, type, text, source, confidence, valid_from, status, project_id, created_at, updated_at, tenant_id) VALUES ('memory-1', 'preference', 'timezone=UTC', 'legacy', 0.9, NULL, 'active', 'legacy-project', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 'local')"
        )
        connection.execute(
            "INSERT INTO repository_events(id, event_type, summary, artifact_id, project_id, details_json, created_at, tenant_id) VALUES ('event-1', 'outcome.recorded', 'Legacy outcome', NULL, 'legacy-project', '{}', '2026-01-01T00:00:00+00:00', 'local')"
        )
        connection.execute(
            "INSERT INTO app_settings(key, value, updated_at) VALUES ('legacy_setting', 'preserve', '2026-01-01T00:00:00+00:00')"
        )
    return database


def _versions(database: Database) -> list[int]:
    with database.connect() as connection:
        return [row["version"] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]


def test_v5_to_v8_preserves_existing_workspace_data_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    database = _legacy_v5_database(path)

    database.migrate()
    assert _versions(database) == list(range(1, 9))
    assert len(list(tmp_path.glob("workspace.sqlite3.backup-before-v6-*"))) == 1
    with database.connect() as connection:
        assert connection.execute("SELECT id, tenant_id FROM conversations WHERE id = 'conversation-1'").fetchone()["tenant_id"] == "local"
        assert connection.execute("SELECT id, project_id, status FROM memories WHERE id = 'memory-1'").fetchone()["status"] == "active"
        assert connection.execute("SELECT id FROM repository_events WHERE id = 'event-1'").fetchone()["id"] == "event-1"
        assert connection.execute("SELECT value FROM tenant_settings WHERE tenant_id = 'local' AND key = 'legacy_setting'").fetchone()["value"] == "preserve"
        assert connection.execute("SELECT actor_id FROM tool_action_confirmations LIMIT 1").fetchall() == []
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'budget_reservations'").fetchone()

    database.migrate()
    assert _versions(database) == list(range(1, 9))
    assert len(list(tmp_path.glob("workspace.sqlite3.backup-before-v6-*"))) == 1


@pytest.mark.parametrize("phase", ["before_schema", "after_statement", "before_receipt"])
def test_migration_failure_rolls_back_schema_and_retains_backup(tmp_path: Path, phase: str) -> None:
    path = tmp_path / f"failure-{phase}.sqlite3"
    _legacy_v5_database(path)

    def fail(version: int, current_phase: str) -> None:
        if version == 6 and current_phase == phase:
            raise sqlite3.OperationalError("simulated disk full or interruption")

    database = Database(path, migration_failure_hook=fail)
    with pytest.raises(MigrationSafetyError, match="rolled back"):
        database.migrate()

    assert _versions(Database(path)) == [1, 2, 3, 4, 5]
    with Database(path).connect() as connection:
        assert connection.execute("SELECT id FROM conversations WHERE id = 'conversation-1'").fetchone()["id"] == "conversation-1"
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'send_scope_receipts'").fetchone() is None
    assert len(list(tmp_path.glob(f"failure-{phase}.sqlite3.backup-before-v6-*"))) == 1


def test_partially_applied_migration_fails_closed_without_guessing(tmp_path: Path) -> None:
    path = tmp_path / "partial.sqlite3"
    database = _legacy_v5_database(path)
    with database.connect() as connection:
        connection.execute("CREATE TABLE send_scope_receipts (id TEXT PRIMARY KEY)")

    with pytest.raises(MigrationSafetyError, match="schema changes without its committed receipt"):
        Database(path).migrate()
    assert _versions(Database(path)) == [1, 2, 3, 4, 5]


def test_malformed_prior_schema_rolls_back_pending_migrations(tmp_path: Path) -> None:
    path = tmp_path / "malformed.sqlite3"
    database = _legacy_v5_database(path)
    with database.connect() as connection:
        connection.execute("DROP TABLE memories")

    with pytest.raises(MigrationSafetyError, match="rolled back"):
        Database(path).migrate()
    assert _versions(Database(path)) == [1, 2, 3, 4, 5]
    with Database(path).connect() as connection:
        assert connection.execute("SELECT id FROM conversations WHERE id = 'conversation-1'").fetchone()["id"] == "conversation-1"
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'send_scope_receipts'").fetchone() is None


def test_locked_database_refuses_to_migrate_without_schema_change(tmp_path: Path) -> None:
    path = tmp_path / "locked.sqlite3"
    database = Database(path)
    database.migrate()
    lock = sqlite3.connect(path, timeout=0.01)
    lock.execute("BEGIN EXCLUSIVE")
    try:
        with pytest.raises(sqlite3.OperationalError):
            Database(path, sqlite_timeout_seconds=0.01).migrate()
    finally:
        lock.rollback()
        lock.close()
    assert _versions(Database(path)) == list(range(1, 9))
