# Backup and move to another computer

Personal AI OS keeps runtime state under `PERSONAL_AI_OS_DATA_DIR` (normally `data`).
Provider keys and access passwords are host secrets and are deliberately excluded from every
backup and transfer archive.

## Create a consistent data backup

The backup command uses SQLite's online backup API, so it can snapshot a running local database
without copying WAL or journal files directly:

```powershell
.\.venv\Scripts\python.exe .\scripts\backup-data.py --data-dir .\data --output-dir .\backups
```

Keep the resulting ZIP somewhere separate from the computer. The repository ignores `backups/`.

## Restore safely

Stop the API before restoring. The restore command verifies the archive, rejects unsafe paths,
and moves any existing data directory aside instead of deleting it:

```powershell
.\.venv\Scripts\python.exe .\scripts\restore-data.py .\backups\personal-ai-os-data-YYYYMMDDTHHMMSSZ.zip --data-dir .\data
```

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
