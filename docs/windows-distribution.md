# Windows distribution, update, and rollback

The community edition's Windows distribution path uses Docker Desktop with
Docker Compose. It therefore needs no local Python, Node.js, or pnpm setup,
and keeps application code separate from the Docker data volume.

Build a reviewable package from a clean commit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows-distribution.ps1 -OutputDirectory .\dist
```

Verify or install it in a dedicated user folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows-distribution.ps1 -Action Install -PackagePath .\dist\personal-ai-os-windows-<version>.zip
```

Use `-CheckOnly` to verify the package manifest and application SHA-256 without
changing an installation. `Status` reports current/available version, migration
version, backup compatibility, signing readiness, and the last update state.

An update creates a consistent data backup before stopping the runtime, retains
the previous application folder, verifies the candidate package, rebuilds the
container, runs the health check, and records `UPDATE_FAILED_SAFE` if it cannot
complete. It never deletes the old application or data backup silently. A
manual `Rollback` restores the previous application version and its compatible
pre-update data snapshot. It does not delete the failed candidate or either
backup, and it records `UPDATE_FAILED_SAFE` if restoration cannot pass health.

Packages are hash-verified, but they are intentionally marked
`SIGNING_EXTERNAL_NOT_CONFIGURED` until a real signing certificate and release
custody are configured outside the repository. No unsigned package is called
signed.
