# Try Personal AI OS without an API key

You can validate the current first-run and privacy-safe startup path without paying for or configuring an OpenAI or Anthropic API key.

## What this proves

The zero-cost readiness check starts the API against a temporary data directory and verifies that:

- the application starts cleanly on a fresh runtime;
- `/health` reports the expected `v0.2.0` runtime version;
- a supported provider is reported as **not configured** when no credential is present;
- Settings keeps secret values hidden;
- no provider model call is made;
- temporary runtime data is removed after the check.

It does **not** certify a real provider connection, model response, or provider-backed conversation. Those remain part of the separate release smoke gate.

## Docker: lowest-friction local start

If Docker Desktop (or Docker Engine with Compose) is already installed, no local Python, Node.js, or pnpm setup is required.

From a fresh checkout, run:

```bash
docker compose up --build -d
```

Then open `http://127.0.0.1:8080`.

The provided Compose configuration binds the application to `127.0.0.1` only, stores runtime data in a named Docker volume, and starts in community mode with authentication disabled for local use. On a fresh checkout with no provider credential configured, starting the container makes no billable model call.

Check container state and logs with:

```bash
docker compose ps
docker compose logs
```

Stop the application while preserving its named data volume with:

```bash
docker compose down
```

Use `docker compose down -v` only when you intentionally want to delete the local Compose data volume as well.

Do not change the port binding to a public interface while authentication is disabled. Public deployments require the documented access controls and trusted HTTPS boundary.

## Windows: prepare a fresh checkout in one command

Prerequisites are Python 3.11+, Node.js 20+, and pnpm 11. The bootstrap does not install system runtimes, does not add a provider credential, and never overwrites an existing `.env` file.

From the repository root, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

The bootstrap validates the prerequisites, creates `.env` from `.env.example` only when `.env` is missing, creates `.venv` only when needed, installs the repository dependencies, and runs the no-key readiness check. It makes no billable provider model call.

To validate only the prerequisites and repository files without changing the working tree or installing dependencies:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -CheckOnly
```

After setup, start the API and web app in separate terminals:

```powershell
.\scripts\dev-api.ps1
```

```powershell
.\scripts\dev-web.ps1
```

Then open `http://localhost:3000`.

## Run only the zero-cost check

If the Python dependencies are already installed, run:

```bash
python scripts/release-provider-smoke.py --provider openai --no-key-only
```

Expected result: the command exits successfully and prints PASS messages for the fresh no-key startup checks.

## Report useful feedback

If the command fails, the no-key UI is confusing, setup steps are unclear, or you find a reproducible bug, open the **Early tester feedback** issue form or add sanitized feedback to Issue #7.

Please include your OS, Python/Node versions when applicable, the exact step that failed, and a minimal reproduction. Never include API keys, `.env` contents, authorization headers, cookies, private conversations, runtime databases, or private project data.

## Want to test the full provider path?

If you already have your own supported provider credential, follow Path B in Issue #7. The full provider path validates connection, model selection, a real text-chat turn, restart persistence, and continued conversation state.
