from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sqlite3
from importlib import metadata
from pathlib import Path
from typing import Any

try:
    from personal_ai_os.config import CANONICAL_DATABASE_FILENAME, LEGACY_DATABASE_FILENAMES
except ModuleNotFoundError:
    # Keep the support script runnable from an uninstalled source checkout.
    CANONICAL_DATABASE_FILENAME = "personal_ai_os.db"
    LEGACY_DATABASE_FILENAMES = ("personal-ai-os.db",)


def _database_health(path: Path, *, location: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "missing",
            "integrity": "not_applicable",
            "migration_version": 0,
            "location": location,
        }
    try:
        with sqlite3.connect(path) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            version = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
        return {
            "status": "ok" if integrity == "ok" else "attention",
            "integrity": integrity,
            "migration_version": int(version),
            "location": location,
        }
    except sqlite3.Error:
        return {
            "status": "attention",
            "integrity": "unavailable",
            "migration_version": None,
            "location": location,
        }


def _database_report(data_dir: Path) -> dict[str, Any]:
    canonical = data_dir / CANONICAL_DATABASE_FILENAME
    if canonical.exists():
        return _database_health(canonical, location="canonical")

    for filename in LEGACY_DATABASE_FILENAMES:
        legacy = data_dir / filename
        if legacy.exists():
            report = _database_health(legacy, location="legacy")
            report["status"] = "legacy_detected"
            return report

    return _database_health(canonical, location="canonical")


def _port_state(port: int) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        return "in_use" if probe.connect_ex(("127.0.0.1", port)) == 0 else "available_or_remote"


def _application_version() -> str:
    """Return packaged version metadata without reading user-owned runtime state."""
    try:
        return metadata.version("personal-ai-os-api")
    except metadata.PackageNotFoundError:
        # This script is also supported directly from a source checkout.
        return "0.3.0-source"


def _backup_health(path: Path) -> dict[str, object]:
    archives = [item for item in path.glob("*.zip") if item.is_file()] if path.is_dir() else []
    return {
        "directory_present": path.is_dir(),
        "archive_count": len(archives),
        "archive_names_exposed": False,
    }


def _update_state(path: Path) -> dict[str, object]:
    """Read only a strict status allowlist so a malformed local file cannot leak data."""
    if not path.is_file():
        return {"metadata_present": False, "status": "NONE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        status = value.get("status") if isinstance(value, dict) else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        status = None
    allowed = {"UPDATING", "INSTALLED", "UPDATED", "ROLLED_BACK", "UPDATE_FAILED_SAFE"}
    return {
        "metadata_present": True,
        "status": status if status in allowed else "UNAVAILABLE_OR_REDACTED",
    }


def collect_report(data_dir: Path, install_dir: Path | None = None) -> dict[str, Any]:
    data_dir = data_dir.resolve()
    install_dir = (install_dir or data_dir.parent).resolve()
    free = shutil.disk_usage(data_dir if data_dir.exists() else data_dir.parent).free
    provider_state = {
        "openai": bool(os.getenv("PERSONAL_AI_OS_OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("PERSONAL_AI_OS_ANTHROPIC_API_KEY")),
        "ollama_enabled": os.getenv("PERSONAL_AI_OS_OLLAMA_ENABLED", "false").lower() in {"1", "true", "yes"},
    }
    recovery_dir = data_dir / "project-recovery"
    return {
        "report": "personal-ai-os-doctor-v2",
        "safe_to_share": True,
        "redaction": "Credential values, headers, cookies, conversations, memory text, database rows, and hidden reasoning are excluded.",
        "runtime": {
            "application_version": _application_version(),
            "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        },
        "data_directory": {
            "location": "configured_local_path_redacted",
            "exists": data_dir.is_dir(),
            "writable": os.access(data_dir if data_dir.exists() else data_dir.parent, os.W_OK),
            "free_bytes": free,
        },
        "database": _database_report(data_dir),
        "providers": {"configured": provider_state, "values_exposed": False},
        "ollama": {"configured": provider_state["ollama_enabled"], "loopback_port": _port_state(11434)},
        "ports": {"api_8000": _port_state(8000), "web_3000": _port_state(3000)},
        "mcp": {"configuration_present": bool(os.getenv("PERSONAL_AI_OS_MCP_STDIO_COMMANDS")), "details_redacted": True},
        "recovery": {"pending_metadata_files": len(list(recovery_dir.glob("*.db"))) if recovery_dir.is_dir() else 0},
        "backups": _backup_health(install_dir / "backups"),
        "update": _update_state(install_dir / "update-state.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Produce a redacted Personal AI OS diagnostic report")
    parser.add_argument("--data-dir", type=Path, default=Path(os.getenv("PERSONAL_AI_OS_DATA_DIR", "data")))
    parser.add_argument("--install-dir", type=Path, help="Optional Windows distribution root; its path is never emitted")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable SAFE_TO_SHARE JSON")
    args = parser.parse_args()
    report = collect_report(args.data_dir, args.install_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print("SAFE_TO_SHARE: true")
    for section, value in report.items():
        if section not in {"report", "safe_to_share", "redaction"}:
            print(f"{section}: {json.dumps(value, sort_keys=True)}")


if __name__ == "__main__":
    main()
