import importlib.util
import json
from pathlib import Path


def _doctor_module():
    path = Path(__file__).parents[3] / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("personal_ai_os_doctor", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
