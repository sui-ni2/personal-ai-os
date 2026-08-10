from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def validate_data_target(data_dir: Path) -> None:
    filesystem_root = Path(data_dir.anchor).resolve()
    user_root = Path.home().resolve()
    if data_dir in {filesystem_root, user_root} or data_dir.parent == data_dir:
        raise SystemExit(f"Refusing to restore into a broad system path: {data_dir}")
    if (data_dir / ".git").exists() or (data_dir / "AGENTS.md").exists():
        raise SystemExit(f"Refusing to replace a project root: {data_dir}")


def safe_extract(bundle: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in bundle.infolist():
        target = (root / member.filename).resolve()
        if root not in target.parents and target != root:
            raise SystemExit("Backup contains an unsafe path")
    bundle.extractall(root)


def restore(archive: Path, data_dir: Path) -> Path | None:
    archive = archive.resolve()
    data_dir = data_dir.resolve()
    validate_data_target(data_dir)
    if not archive.is_file():
        raise SystemExit(f"Backup does not exist: {archive}")
    prior_backup: Path | None = None
    with tempfile.TemporaryDirectory(prefix="personal-ai-os-restore-") as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None:
                raise SystemExit("Backup archive is corrupt")
            safe_extract(bundle, staging)
        manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("format") != "personal-ai-os-data-backup-v1":
            raise SystemExit("Unsupported backup format")
        restored_data = staging / "data"
        if not restored_data.is_dir():
            raise SystemExit("Backup does not contain a data directory")
        if data_dir.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            prior_backup = data_dir.with_name(f"{data_dir.name}.before-restore-{timestamp}")
            if prior_backup.exists():
                raise SystemExit(f"Safety backup path already exists: {prior_backup}")
            data_dir.replace(prior_backup)
        try:
            shutil.copytree(restored_data, data_dir)
        except Exception:
            if data_dir.exists():
                shutil.rmtree(data_dir)
            if prior_backup is not None:
                prior_backup.replace(data_dir)
            raise
    return prior_backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a Personal AI OS data backup safely")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    prior = restore(args.archive, args.data_dir)
    print(f"Restored data to {args.data_dir.resolve()}")
    if prior:
        print(f"Previous data preserved at {prior}")


if __name__ == "__main__":
    main()
