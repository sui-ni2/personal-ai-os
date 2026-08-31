from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALLER = REPO_ROOT / "scripts" / "install-windows-distribution.ps1"


def _package(path: Path, *, valid_hash: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    application = path / "application.zip"
    with zipfile.ZipFile(application, "w") as archive:
        archive.writestr("compose.yaml", "services: {}\n")
    digest = hashlib.sha256(application.read_bytes()).hexdigest()
    manifest = {
        "format": "personal-ai-os-windows-distribution-v1",
        "version": "fixture-1",
        "application_sha256": digest if valid_hash else "0" * 64,
        "migration_version": 8,
        "backup_compatibility": "personal-ai-os-data-backup-v1",
        "signing_status": "SIGNING_EXTERNAL_NOT_CONFIGURED",
    }
    manifest_path = path / "personal-ai-os-release.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    package = path / "personal-ai-os-windows-fixture.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.write(application, "application.zip")
        archive.write(manifest_path, "personal-ai-os-release.json")
    return package


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(INSTALLER), *arguments],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


@pytest.mark.skipif(not INSTALLER.exists(), reason="Windows distribution script is not present")
def test_windows_distribution_check_only_accepts_hashed_unicode_and_space_path(tmp_path: Path) -> None:
    package = _package(tmp_path / "release")
    install_path = tmp_path / "安装 空间"
    completed = _run(
        "-Action", "Install", "-PackagePath", str(package), "-InstallPath", str(install_path), "-CheckOnly"
    )
    assert completed.returncode == 0, completed.stderr
    assert "Verification" in completed.stdout and "PASS" in completed.stdout
    assert not (install_path / "installation.json").exists()


@pytest.mark.skipif(not INSTALLER.exists(), reason="Windows distribution script is not present")
def test_windows_distribution_check_only_rejects_checksum_mismatch_without_creating_installation(tmp_path: Path) -> None:
    package = _package(tmp_path / "mismatch", valid_hash=False)
    install_path = tmp_path / "must remain empty"
    completed = _run(
        "-Action", "Install", "-PackagePath", str(package), "-InstallPath", str(install_path), "-CheckOnly"
    )
    assert completed.returncode != 0
    assert "hash" in (completed.stderr + completed.stdout).lower()
    assert not (install_path / "installation.json").exists()


@pytest.mark.skipif(not INSTALLER.exists(), reason="Windows distribution script is not present")
def test_windows_distribution_refuses_rollback_without_snapshot_before_docker_access(tmp_path: Path) -> None:
    install_path = tmp_path / "fixture install"
    completed = _run("-Action", "Rollback", "-InstallPath", str(install_path), "-NoLaunch")
    assert completed.returncode != 0
    assert "No rollback application snapshot is available" in (completed.stderr + completed.stdout)
