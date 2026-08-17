# Contributing to Personal AI OS

Thank you for helping improve Personal AI OS. Contributions should keep the core
general-purpose, local-first, auditable, and safe for private user data.

## Good first contributions

If you are new to the project, the highest-value contribution is to try a fresh install and report
real setup or first-chat friction in [Issue #7](https://github.com/sui-ni2/personal-ai-os/issues/7).
Small documentation corrections and focused bug fixes are also welcome. Please do not create
synthetic feedback or test data that could be mistaken for real user adoption.

You do **not** need a paid provider API key to verify the safe first-run path.

### Lowest-friction runtime check with Docker

If Docker Desktop (or Docker Engine with Compose) is already installed:

```bash
docker compose up --build -d
```

Open `http://127.0.0.1:8080`. The default Compose profile is loopback-only and stores runtime data
in a named Docker volume. Stop it with `docker compose down`; add `-v` only when you intentionally
want to delete that local data volume.

### Windows source checkout

On Windows with Python 3.11+, Node.js 20+, and pnpm 11 installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

The bootstrap preserves an existing `.env` and `.venv`, installs repository dependencies, and runs
the isolated no-key readiness check. It adds no provider credential and makes no billable model
call. Use `-CheckOnly` when you only want to validate prerequisites without changing the checkout.

### Manual no-key gate

If the Python dependencies are already installed, run:

```powershell
.\.venv\Scripts\python.exe scripts\release-provider-smoke.py --provider openai --no-key-only
```

This starts an isolated temporary API runtime with provider credentials stripped, verifies the
`v0.2.0` health contract, confirms the selected provider remains unconfigured, and confirms secret
values are not exposed through Settings. It makes no billable model call and deletes its temporary
runtime data when complete.

## Before opening a change

- Search existing issues before starting overlapping work.
- Keep project plugins behind the project contract; do not add domain-specific fields to
  the core Chat, Memory, Repository, provider, or execution-event schemas.
- Never commit credentials, `.env` files, runtime databases, conversations, logs,
  uploads, backups, browser data, or private project artifacts.
- Discuss persistent-data migrations and security-boundary changes before implementation.

## Local source setup

Prerequisites are Node.js 20 or newer with pnpm 11 and Python 3.11 or newer.

On Windows, prefer the verified bootstrap above. For a manual setup:

```powershell
Copy-Item .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
pnpm install --frozen-lockfile
```

Use only placeholder values in `.env.example`. Never attach a real `.env` file to an
issue or pull request.

## Checks

Run the smallest relevant checks while developing and the complete gates before a pull
request:

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q
.\.venv\Scripts\python.exe -m compileall -q apps/api/src packages
.\.venv\Scripts\python.exe scripts\release-provider-smoke.py --provider openai --no-key-only
pnpm check:web
pnpm build:web
```

Changes to `Dockerfile`, `compose.yaml`, Windows setup, application packages, or platform-readiness
workflows also run the repository's Platform Readiness workflow, which exercises the Docker Compose
path and the Windows bootstrap end to end.

## Pull requests

- Keep changes focused and explain the user-visible outcome.
- Include tests for behavior changes and describe the checks that passed.
- Call out schema, permission, MCP, authentication, or deployment changes explicitly.
- Do not include generated runtime data or unrelated formatting changes.

By submitting a contribution, you agree that it is licensed under Apache-2.0.