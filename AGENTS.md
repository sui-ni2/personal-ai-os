# Personal AI OS project rules

## Purpose

Build the independent Personal AI OS modular monolith. V0.2 focuses on a mobile-first product UI and unified visual system for the existing Next.js workbench backed by FastAPI, SQLite, provider adapters, auditable SSE activity, MCP/tool integration, structured memory, repository events, and project plugins.

## Important commands

- Install JavaScript dependencies: `pnpm install`
- Install Python dependencies: `python -m pip install -r requirements-dev.txt`
- Start API: `.\scripts\dev-api.ps1`
- Start web: `pnpm --filter @personal-ai-os/web dev`
- Backend tests: `python -m pytest apps/api/tests`
- Frontend checks: `pnpm --filter @personal-ai-os/web lint && pnpm --filter @personal-ai-os/web typecheck`

## Files and directories not to touch

- Never access, print, modify, or commit `.env`, API keys, tokens, credentials, browser profiles, or cookies.
- Do not read or modify `euro-football-ml`, Soccer source repositories, lottery projects, or any directory outside this repository.
- Treat `data/`, runtime databases, logs, uploaded files, and repository history as user data; do not delete them without explicit approval.
- Do not add Soccer-specific fields or assumptions to core Chat, Memory, Repository, provider, or execution-event schemas.

## Backup and reversibility

- Keep work in Git and prefer small, reviewable changes.
- Before changing an existing persistent-data schema, create a migration and a recoverable database backup.
- Do not rewrite Git history or discard user changes.

## Test and check commands

- Smallest backend gate: `python -m pytest apps/api/tests -q`
- Backend syntax gate: `python -m compileall -q apps/api/src packages`
- Frontend gate: `pnpm --filter @personal-ai-os/web typecheck`
- Production web build: `pnpm --filter @personal-ai-os/web build`

## Project-specific safety rules

- API keys are server-side environment variables only. Never return key values from an API.
- Execution traces may expose event summaries, tool names, sources, status, and duration, but never raw private chain-of-thought.
- MCP and internal tools must be allowlisted, permission-checked, and auditable. Never execute model-supplied shell commands.
- Project plugins register metadata, context, tools, views, artifacts, and permissions through the project contract.
- General must remain a working project when the Soccer example plugin is absent.
- V0.1 remains a modular monolith; do not introduce microservices, HealthKit, full calendar sync, or multi-user collaboration.
