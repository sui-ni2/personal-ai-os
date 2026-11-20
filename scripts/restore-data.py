from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath


def validate_data_target(data_dir: Path) -> None:
    filesystem_root = Path(data_dir.anchor).resolve()
    user_root = Path.home().resolve()
    if data_dir in {filesystem_root, user_root} or data_dir.parent == data_dir:
        raise SystemExit(f"Refusing to restore into a broad system path: {data_dir}")
    if (data_dir / ".git").exists() or (data_dir / "AGENTS.md").exists():
        raise SystemExit(f"Refusing to replace a project root: {data_dir}")


_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
    "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
}


def _normalize_archive_path(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name or "\\" in name:
        raise SystemExit("Backup contains an unsafe path")
    raw = name[:-1] if name.endswith("/") else name
    parts = raw.split("/")
    windows_path = PureWindowsPath(raw)
    if (
        not raw
        or raw.startswith("/")
        or PurePosixPath(raw).is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or any(
            part in {"", ".", ".."}
            or part.endswith((" ", "."))
            or part.split(".", maxsplit=1)[0].upper() in _WINDOWS_RESERVED_NAMES
            or any(ord(character) < 32 or character in '<>:"|?*' for character in part)
            for part in parts
        )
    ):
        raise SystemExit("Backup contains an unsafe path")
    return "/".join(parts)


def safe_extract(bundle: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    root.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for member in bundle.infolist():
        normalized = _normalize_archive_path(member.filename)
        if normalized not in {"data", "manifest.json"} and not normalized.startswith("data/"):
            raise SystemExit("Backup contains a path outside its data directory")
        if normalized == "manifest.json" and member.is_dir():
            raise SystemExit("Backup manifest must be a file")
        if normalized == "data" and not member.is_dir():
            raise SystemExit("Backup data root must be a directory")
        key = normalized.casefold()
        if key in seen:
            raise SystemExit("Backup contains duplicate or case-colliding paths")
        seen.add(key)
        if member.flag_bits & 0x1:
            raise SystemExit("Encrypted backup entries are not supported")
        mode = (member.external_attr >> 16) & 0xFFFF
        file_type = stat.S_IFMT(mode)
        if file_type == stat.S_IFLNK or file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise SystemExit("Backup contains a link or unsupported filesystem entry")
        if member.is_dir() and file_type == stat.S_IFREG:
            raise SystemExit("Backup directory entry has an invalid file type")
        if not member.is_dir() and file_type == stat.S_IFDIR:
            raise SystemExit("Backup file entry has an invalid directory type")
        target = root.joinpath(*normalized.split("/")).resolve()
        if target != root and root not in target.parents:
            raise SystemExit("Backup contains an unsafe path")
    bundle.extractall(root)


def _verify_manifest_files(manifest: dict[str, object], restored_data: Path) -> None:
    if "files" not in manifest:
        return  # Backward compatibility with earlier v1 archives.
    records = manifest["files"]
    if not isinstance(records, list):
        raise SystemExit("Backup manifest contains an invalid file list")
    root = restored_data.resolve()
    expected: dict[str, tuple[int, str]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise SystemExit("Backup manifest contains an invalid file entry")
        relative = record.get("path")
        size = record.get("size_bytes")
        digest = record.get("sha256")
        if not isinstance(relative, str):
            raise SystemExit("Backup manifest contains an invalid file path")
        normalized = _normalize_archive_path(relative)
        if normalized in {"data", "manifest.json"} or normalized.startswith("data/"):
            raise SystemExit("Backup manifest contains an invalid data-relative path")
        if (
            type(size) is not int
            or size < 0
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise SystemExit("Backup manifest contains invalid integrity metadata")
        key = normalized.casefold()
        if key in expected:
            raise SystemExit("Backup manifest contains duplicate or case-colliding paths")
        candidate = restored_data.joinpath(*normalized.split("/"))
        resolved = candidate.resolve()
        if root not in resolved.parents or candidate.is_symlink() or not candidate.is_file():
            raise SystemExit(f"Backup manifest references a missing or unsafe file: {relative}")
        actual_digest = hashlib.sha256()
        actual_size = 0
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                actual_digest.update(chunk)
                actual_size += len(chunk)
        if actual_size != size or actual_digest.hexdigest() != digest:
            raise SystemExit(f"Backup integrity check failed for {relative}")
        expected[key] = (size, digest)
    actual: set[str] = set()
    for path in restored_data.rglob("*"):
        if path.is_symlink():
            raise SystemExit("Restored data contains an unexpected symbolic link")
        if path.is_dir():
            continue
        if not path.is_file():
            raise SystemExit("Restored data contains an unsupported filesystem entry")
        key = path.relative_to(restored_data).as_posix().casefold()
        if key in actual:
            raise SystemExit("Restored data contains duplicate or case-colliding paths")
        actual.add(key)
    if actual != set(expected):
        raise SystemExit("Backup data files do not match the integrity manifest")


def restore(archive: Path, data_dir: Path) -> Path | None:
    archive = archive.expanduser().resolve()
    requested_data_dir = data_dir.expanduser()
    if requested_data_dir.is_symlink():
        raise SystemExit("Refusing to restore through a symbolic-link data directory")
    data_dir = requested_data_dir.resolve()
    validate_data_target(data_dir)
    if data_dir.exists() and not data_dir.is_dir():
        raise SystemExit(f"Restore target exists but is not a directory: {data_dir}")
    if not archive.is_file():
        raise SystemExit(f"Backup does not exist: {archive}")
    prior_backup: Path | None = None
    with tempfile.TemporaryDirectory(prefix="personal-ai-os-restore-") as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None:
                raise SystemExit("Backup archive is corrupt")
            safe_extract(bundle, staging)
        manifest_path = staging / "manifest.json"
        if not manifest_path.is_file() or manifest_path.is_symlink():
            raise SystemExit("Backup manifest is missing or unsafe")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit("Backup manifest is invalid") from exc
        if not isinstance(manifest, dict) or manifest.get("format") != "personal-ai-os-data-backup-v1":
            raise SystemExit("Unsupported backup format")
        restored_data = staging / "data"
        if not restored_data.is_dir() or restored_data.is_symlink():
            raise SystemExit("Backup does not contain a safe data directory")
        _verify_manifest_files(manifest, restored_data)
        data_dir.parent.mkdir(parents=True, exist_ok=True)
        if data_dir.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            prior_backup = data_dir.with_name(f"{data_dir.name}.before-restore-{timestamp}")
            if prior_backup.exists() or prior_backup.is_symlink():
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
