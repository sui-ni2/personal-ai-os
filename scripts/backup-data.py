from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def snapshot_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source)) as source_db, closing(
        sqlite3.connect(destination)
    ) as destination_db:
        source_db.backup(destination_db)
        destination_db.commit()


def build_backup(data_dir: Path, output_dir: Path) -> Path:
    data_dir = data_dir.resolve()
    output_dir = output_dir.resolve()
    if not data_dir.is_dir():
        raise SystemExit(f"Data directory does not exist: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = output_dir / f"personal-ai-os-data-{timestamp}.zip"
    with tempfile.TemporaryDirectory(prefix="personal-ai-os-backup-") as temporary:
        staging = Path(temporary) / "data"
        for source in data_dir.rglob("*"):
            relative = source.relative_to(data_dir)
            destination = staging / relative
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif source.suffix in {".db", ".sqlite", ".sqlite3"}:
                snapshot_database(source, destination)
            elif not any(source.name.endswith(suffix) for suffix in ("-wal", "-shm", "-journal")):
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        manifest = {
            "format": "personal-ai-os-data-backup-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_name": data_dir.name,
        }
        (Path(temporary) / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for item in Path(temporary).rglob("*"):
                if item.is_file():
                    bundle.write(item, item.relative_to(temporary))
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None or "manifest.json" not in bundle.namelist():
            archive.unlink(missing_ok=True)
            raise SystemExit("Backup verification failed")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a consistent Personal AI OS data backup")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    args = parser.parse_args()
    print(build_backup(args.data_dir, args.output_dir))


if __name__ == "__main__":
    main()
