# Personal AI OS V0.1

A mobile-first, general-purpose AI workbench built as a modular monolith. Chat, structured memory, repository events, providers, auditable execution traces, MCP tools, and project plugins share one core without making Soccer a system-level concern.

## What is runnable now

- Next.js App Shell with Chat, Memory, Repository, Projects, and Settings views.
- FastAPI API with SQLite persistence and automatic schema migration.
- OpenAI and Anthropic adapters behind one streaming interface.
- SSE execution protocol: `message`, `tool_start`, `tool_result`, `error`, `done`.
- Allowlisted MCP gateway with a stateless JSON-RPC `system.echo` reference server.
- General and Soccer project plugins using the same project contract.
- API and boundary tests.

Provider calls require server-side environment variables. The application still starts without keys and reports each provider as unconfigured without exposing secret values.

## Start locally

Prerequisites: Node.js 20+ with pnpm, and Python 3.11+.

```powershell
Copy-Item .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
pnpm install
```

In terminal 1:

```powershell
.\scripts\dev-api.ps1
```

In terminal 2:

```powershell
.\scripts\dev-web.ps1
```

Open `http://localhost:3000`. The API health endpoint is `http://localhost:8000/health`.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall -q apps/api/src packages
pnpm check:web
pnpm build:web
```

## Boundaries

- The core schemas contain no Soccer-specific fields.
- Execution traces contain observable status and tool summaries, never raw private chain-of-thought.
- Secrets stay in server-side environment variables and are never returned by Settings.
- MCP tools are registered and allowlisted; the model cannot supply shell commands.
- V0.1 is a modular monolith, not a microservice system.

See `docs/implementation-decisions.md` for the quick specification consistency check and `docs/architecture.md` for the package boundaries.
