from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def snapshot_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source)) as source_db, closing(
        sqlite3.connect(destination)
    ) as destination_db:
        source_db.backup(destination_db)
        destination_db.commit()


_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
    "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
}


def _assert_portable_relative_path(relative: str) -> None:
    if not relative or "\\" in relative or ":" in relative or relative.startswith("/"):
        raise SystemExit(f"Backup data contains a non-portable path: {relative}")
    for part in relative.split("/"):
        device_name = part.split(".", maxsplit=1)[0].upper()
        if (
            not part
            or part in {".", ".."}
            or part.endswith((" ", "."))
            or device_name in _WINDOWS_RESERVED_NAMES
            or any(ord(character) < 32 or character in '<>:"|?*' for character in part)
        ):
            raise SystemExit(f"Backup data contains a non-portable path: {relative}")


def _file_manifest(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise SystemExit(f"Backup data contains a symlink; refusing to follow it: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise SystemExit(f"Backup data contains an unsupported filesystem entry: {path}")
        relative = path.relative_to(root).as_posix()
        _assert_portable_relative_path(relative)
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        records.append({"path": relative, "size_bytes": size, "sha256": digest.hexdigest()})
    return records


def build_backup(data_dir: Path, output_dir: Path) -> Path:
    data_dir = data_dir.resolve()
    output_dir = output_dir.resolve()
    if not data_dir.is_dir():
        raise SystemExit(f"Data directory does not exist: {data_dir}")
    if output_dir == data_dir or data_dir in output_dir.parents:
        raise SystemExit("Backup output directory must be outside the data directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = output_dir / f"personal-ai-os-data-{timestamp}-{uuid4().hex}.zip"
    with tempfile.TemporaryDirectory(prefix="personal-ai-os-backup-") as temporary:
        staging = Path(temporary) / "data"
        staging.mkdir()
        for source in data_dir.rglob("*"):
            if source.is_symlink():
                raise SystemExit(f"Backup data contains a symlink; refusing to follow it: {source}")
            relative = source.relative_to(data_dir)
            _assert_portable_relative_path(relative.as_posix())
            destination = staging / relative
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif source.is_file():
                if source.suffix in {".db", ".sqlite", ".sqlite3"}:
                    snapshot_database(source, destination)
                elif not source.name.endswith(("-wal", "-shm", "-journal")):
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            else:
                raise SystemExit(f"Backup data contains an unsupported filesystem entry: {source}")
        files = _file_manifest(staging)
        manifest = {
            "format": "personal-ai-os-data-backup-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_name": data_dir.name,
            "files": files,
        }
        (Path(temporary) / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(staging, "data/")
            for item in Path(temporary).rglob("*"):
                if item == staging:
                    continue
                relative_item = item.relative_to(temporary).as_posix()
                if item.is_dir():
                    bundle.write(item, f"{relative_item}/")
                elif item.is_file():
                    bundle.write(item, relative_item)
    try:
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None or "manifest.json" not in bundle.namelist():
                raise ValueError("archive CRC or manifest check failed")
            archived_manifest = json.loads(bundle.read("manifest.json"))
            if archived_manifest.get("format") != "personal-ai-os-data-backup-v1":
                raise ValueError("unsupported backup manifest")
            records = archived_manifest.get("files")
            if not isinstance(records, list):
                raise ValueError("backup manifest file list is missing")
            expected: set[str] = set()
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError("invalid backup manifest entry")
                relative = record.get("path")
                size = record.get("size_bytes")
                digest = record.get("sha256")
                if (
                    not isinstance(relative, str)
                    or not relative
                    or "\\" in relative
                    or ":" in relative
                    or relative.startswith("/")
                    or ".." in Path(relative).parts
                    or type(size) is not int
                    or size < 0
                    or not isinstance(digest, str)
                    or len(digest) != 64
                ):
                    raise ValueError("invalid backup manifest entry")
                name = f"data/{relative}"
                if name.casefold() in expected:
                    raise ValueError("duplicate backup manifest path")
                expected.add(name.casefold())
                actual_digest = hashlib.sha256()
                actual_size = 0
                with bundle.open(name) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        actual_digest.update(chunk)
                        actual_size += len(chunk)
                if actual_size != size or actual_digest.hexdigest() != digest:
                    raise ValueError(f"backup integrity check failed for {relative}")
            actual = {
                name.casefold()
                for name in bundle.namelist()
                if name.startswith("data/") and not name.endswith("/")
            }
            if actual != expected:
                raise ValueError("backup archive contents do not match the manifest")
    except Exception as exc:
        archive.unlink(missing_ok=True)
        raise SystemExit("Backup verification failed") from exc
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a consistent Personal AI OS data backup")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    args = parser.parse_args()
    print(build_backup(args.data_dir, args.output_dir))


if __name__ == "__main__":
    main()
