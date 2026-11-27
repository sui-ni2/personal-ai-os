# Backup and move to another computer

Personal AI OS keeps runtime state under `PERSONAL_AI_OS_DATA_DIR` (normally `data`).
Provider keys and access passwords are host secrets and are deliberately excluded from every
backup and transfer archive.

The canonical core database is always `PERSONAL_AI_OS_DATA_DIR/personal_ai_os.db`.
Backup and restore preserve that file together with the rest of the data directory. Doctor reads
that canonical location; if it finds the former diagnostic-only `personal-ai-os.db` name instead,
it reports it as legacy without moving or deleting user data.

## Create a consistent data backup

The backup command uses SQLite's online backup API, so it can snapshot a running local database
without copying WAL or journal files directly:

```powershell
.\.venv\Scripts\python.exe .\scripts\backup-data.py --data-dir .\data --output-dir .\backups
```

Keep the resulting ZIP somewhere separate from the computer. The repository ignores `backups/`.
Each backup has a timestamp and unique suffix; repeated runs keep earlier archives intact.
An archive-name collision fails rather than overwriting a backup. Empty data directories also
produce a restorable backup. The archive format remains `personal-ai-os-data-backup-v1`, and
existing backups remain compatible with the restore command.

New archives include a SHA-256 digest and byte count for every backed-up data file. The
archive is verified against that manifest before it is returned, and restore verifies the
same manifest before moving the current data directory. Older v1 archives without the
file-digest list remain restorable. Empty nested directories are retained as well. A backup
refuses to follow symlinks or special files, and the output directory must be outside the data
directory so previous archives cannot become recursive backup input. Case-colliding
source paths, including directory names, fail before an archive is created. Manifest
paths are relative to the inner data directory; ordinary user files named
`manifest.json` and nested `data/` paths remain restorable.

## Restore safely

Stop the API before restoring. The restore command verifies the archive and its SHA-256 file manifest before touching the
current data directory. It rejects absolute/traversal paths, Windows path aliases,
symlinks, special files, duplicate/case-colliding entries (including implicit parent
directories), file/directory conflicts, and unexpected archive roots.
It then moves any existing data directory aside instead of deleting it:

```powershell
.\.venv\Scripts\python.exe .\scripts\restore-data.py .\backups\personal-ai-os-data-<timestamp>-<unique-suffix>.zip --data-dir .\data
```

## Migration safety

Before applying pending database migrations, the application creates a uniquely named
SQLite online-backup snapshot. It checks the snapshot's SQLite integrity and recorded
schema versions before beginning the migration transaction. If snapshot creation or
verification fails, the migration does not start. Repeated attempts retain distinct
pre-migration snapshots rather than replacing an earlier recovery point.

## Make one transfer package

After committing the desired source state:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export-transfer-package.ps1
```

The generated archive contains the committed source plus a verified data backup. It does not
contain `.env`, model keys, access passwords, browser state, virtual environments, build caches,
or Git history.

On the destination computer, extract it, recreate `.venv`, install Python and pnpm dependencies,
restore the ZIP in `transfer-data/`, and enter secrets in that computer's environment or hosting
secret store. Never send model keys inside the transfer package.
