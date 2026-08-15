# Personal AI OS

[![CI](https://github.com/sui-ni2/personal-ai-os/actions/workflows/ci.yml/badge.svg)](https://github.com/sui-ni2/personal-ai-os/actions/workflows/ci.yml)

A user-controlled AI workspace for long-running projects. It preserves context, helps complete
work, and turns useful results into reusable outcomes while keeping memory decisions visible to
the user. One modular core supports a community/self-hosted delivery mode today and a fail-closed
managed cloud boundary for future account-based delivery.

![Personal AI OS flow](apps/web/public/assets/personal-ai-flow.png)

## Early testers wanted

Personal AI OS is preparing its first stable `v0.2.0` release. The most useful contribution right
now is a genuine fresh-install test: configure a supported provider, complete one text-chat turn,
restart the app, and report any setup friction or reproducible bug.

- Testers: use [Issue #7](https://github.com/sui-ni2/personal-ai-os/issues/7) for sanitized feedback.
- Contributors: focused documentation fixes, bug fixes, and small pull requests are welcome.
- Never post API keys, `.env` files, authorization headers, cookies, private conversations,
  runtime databases, logs containing secrets, uploads/backups, or private project data.

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
- General, Soccer, and isolated P5 / 排列5 project plugins using the same project contract.
- P5 daily review-first workflow with a Beijing 22:22 result gate, immutable 10,000-candidate
  zero-stake observation locks, diagnostic Top10/Top5 prefixes, candidate lookup, cumulative
  rule evidence, conflict rejection, and audit views.
- API and boundary tests.
- Explicit community/cloud product contracts, tenant-scoped core persistence, and
  capability-based access to advanced features. The runnable distribution remains the
  community edition; cloud accounts, billing, managed routing, and device sync are not yet live.

Provider calls require server-side environment variables. The application still starts without keys and reports each provider as unconfigured without exposing secret values.

Public deployments can enable the built-in single-user access gate with
`PERSONAL_AI_OS_REQUIRE_AUTH=true`. The access password and 32+ character session secret remain
server-side, while the phone receives only an HTTP-only signed session cookie.

GPT Live uses a server-mediated WebRTC session so provider keys never reach the browser.
By default it uses `PERSONAL_AI_OS_OPENAI_API_KEY` with OpenAI's calls endpoint. A
separate `PERSONAL_AI_OS_REALTIME_API_KEY` can be used instead. An alternative provider
requires both that independent key and an explicit `PERSONAL_AI_OS_REALTIME_ENDPOINT`;
the standard OpenAI key is never forwarded to a custom endpoint. The endpoint must be an
HTTPS URL ending in `/realtime/calls` and implement the same multipart SDP/session contract.
Model overrides are `PERSONAL_AI_OS_REALTIME_MODEL`, `PERSONAL_AI_OS_REALTIME_VOICE`,
and `PERSONAL_AI_OS_REALTIME_TRANSCRIPTION_MODEL`.

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

Do not use a plain LAN HTTP address as the final phone path: GPT Live needs a trusted HTTPS
secure context. See `docs/mobile-deployment.md` for the single-origin deployment contract,
physical-device checklist, and the post-deployment verifier.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall -q apps/api/src packages
pnpm check:web
pnpm build:web
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-mobile-readiness.ps1 -BaseUrl "http://127.0.0.1:3001" -AllowInsecureLocalhost
```

## Boundaries

- The core schemas contain no Soccer-specific fields.
- P5 owns `data/projects/p5/p5.db`; it adds no P5 fields to Chat, Memory, or Repository and
  exposes no P3 or Codex path.
- Execution traces contain observable status and tool summaries, never raw private chain-of-thought.
- Audit payloads are recursively bounded and redact nested credentials, authorization headers,
  cookies, tracebacks, and reasoning fields before new events are persisted or streamed.
- Secrets stay in server-side environment variables and are never returned by Settings.
- MCP tools are registered and allowlisted; the model cannot supply shell commands.
- HTTP connector endpoints and stdio aliases are operator configuration; discovered tools
  must still be explicitly added to each connector's `allowed_tools` list.
- V0.1 is a modular monolith, not a microservice system.
- Community and cloud are delivery modes of one product core, not separate applications.
- Core storage is tenant-scoped. Cloud mode refuses to start until real account identity is ready.
- Ordinary UI language uses AI service, Tools, Outcomes, and Activity; Provider, MCP, Repository,
  and execution internals belong to Advanced Settings.

## Open source and privacy

Personal AI OS is licensed under Apache-2.0. The repository contains application code,
tests, documentation, and non-secret configuration examples. It does not include or
license a user's runtime databases, conversations, credentials, logs, uploads, backups,
or private project artifacts.

The root package remains marked `private` to prevent accidental publication to the npm
registry; this does not restrict use of the source code under Apache-2.0. See
`CONTRIBUTING.md` before submitting a change and `SECURITY.md` before reporting a
security issue. The initial problem statement and honest first-party usage case are
documented in `docs/dogfooding.md`.

The focused path from the current prototype to a usable public product is in
`ROADMAP.md`.
The positioning, delivery-mode, terminology, capability, and tenant contracts are in
`docs/product-contract.md`.

## License

Copyright 2026 Personal AI OS contributors. Licensed under the Apache License, Version
2.0. See `LICENSE`.

See `docs/implementation-decisions.md` for the quick specification consistency check and `docs/architecture.md` for the package boundaries.
See `docs/p5-project-plugin.md` for the P5 daily contract, API, tools, storage, and views.
See `docs/transfer-and-backup.md` for verified backups, safe restore, and moving the app to another computer.