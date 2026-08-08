# Personal AI OS V0.2

A mobile-first, general-purpose AI workbench built as a modular monolith. Chat, structured memory, repository events, providers, auditable execution traces, MCP tools, and project plugins share one core without making Soccer a system-level concern.

## What is runnable now

- Next.js App Shell with Chat, Memory, Repository, Projects, and Settings views.
- Installable mobile PWA shell with standalone display, app icons, safe-area-aware
  navigation, and a production service worker for the cached app shell.
- Focused Text and GPT Live conversation modes. Completed Live transcripts stay in the
  same conversation, update its short title, and do not become long-term Memory automatically.
- FastAPI API with SQLite persistence and automatic schema migration.
- OpenAI and Anthropic adapters behind one streaming interface, with timeout,
  cancellation, bounded retry, rate-limit normalization, and interrupted-stream handling.
- SSE execution protocol: `message`, `tool_start`, `tool_result`, `error`, `done`.
- Restart-safe conversation history with project filtering and restored execution traces.
- Allowlisted MCP gateway with a stateless JSON-RPC `system.echo` reference server plus
  configurable HTTP and fixed-command-alias stdio connectors.
- General and Soccer project plugins using the same project contract.
- API and boundary tests.

Provider calls require server-side environment variables. The application still starts without keys and reports each provider as unconfigured without exposing secret values.

GPT Live uses a server-mediated WebRTC session so the standard OpenAI key never reaches
the browser. It uses `PERSONAL_AI_OS_OPENAI_API_KEY`; optional model overrides are
`PERSONAL_AI_OS_REALTIME_MODEL`, `PERSONAL_AI_OS_REALTIME_VOICE`, and
`PERSONAL_AI_OS_REALTIME_TRANSCRIPTION_MODEL`.

stdio connectors are configured server-side through
`PERSONAL_AI_OS_MCP_STDIO_COMMANDS`. Each entry maps a display alias to one fixed argv
array whose executable is an absolute path. The browser and model can select an alias;
they cannot submit a command or shell string.

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

## Install on a phone

For local desktop testing, use the URL above. Installing on a separate phone requires an
HTTPS deployment that can reach the API. Open the deployed app in the phone browser and
choose **More → Install app** when the browser offers installation. On iOS, use Safari's
**Add to Home Screen** action if the install prompt is not shown.

The cached shell can open without a network connection, but provider calls, GPT Live,
memory, and repository data still require the API.

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
- HTTP connector endpoints and stdio aliases are operator configuration; discovered tools
  must still be explicitly added to each connector's `allowed_tools` list.
- V0.1 is a modular monolith, not a microservice system.

See `docs/implementation-decisions.md` for the quick specification consistency check and `docs/architecture.md` for the package boundaries.
