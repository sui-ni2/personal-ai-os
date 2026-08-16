# Personal AI OS project rules

## Purpose

Build the independent Personal AI OS modular monolith as one user-controlled AI workspace with
community/self-hosted and managed-cloud delivery contracts. The runnable product remains the
community edition until account identity, tenant resolution, and billing are complete. The core
includes the Next.js experience, FastAPI, tenant-scoped SQLite, provider adapters, auditable SSE
activity, MCP/tool integration, structured memory, outcomes, and project plugins.

## Important commands

- Install JavaScript dependencies: `pnpm install`
- Install Python dependencies: `python -m pip install -r requirements-dev.txt`
- Start API: `.\scripts\dev-api.ps1`
- Start web: `pnpm --filter @personal-ai-os/web dev`
- Build the single-origin static frontend: `pnpm build:static`
- Create a consistent data backup: `.\.venv\Scripts\python.exe .\scripts\backup-data.py --data-dir .\data --output-dir .\backups`
- Backend tests: `python -m pytest apps/api/tests`
- Frontend checks: `pnpm --filter @personal-ai-os/web lint && pnpm --filter @personal-ai-os/web typecheck`

## Codex account handoff trial

The local repository and its Git state are the continuity boundary. A ChatGPT/Codex account session is not the source of truth.

- At the start of a Codex work session, if `.local-state/codex-handoff/FACTS.md` or `.local-state/codex-handoff/HANDOFF.md` exists, read both before changing files. Compare the recorded branch/HEAD with the current repository; if the factual snapshot is missing or stale, run `python scripts/codex-handoff.py` first.
- When the user says they are switching accounts, changing accounts, handing off, or asks another account to continue, run `python scripts/codex-handoff.py`, then refresh `.local-state/codex-handoff/HANDOFF.md` with only compact semantic context Git cannot reconstruct: Objective, Completed, Decisions/constraints, Blockers, and Next action.
- Keep `HANDOFF.md` concise (target <= 80 lines). Do not copy chat transcripts, credentials, tokens, cookies, private chain-of-thought, or large source/diff bodies into it.
- If a prior account stopped before creating a semantic handoff, the next account must run `python scripts/codex-handoff.py`, inspect the current Git/files, reconstruct only what can be supported by local evidence, and mark any remaining context gap instead of inventing it.
- Current files and Git state override a stale handoff. Record the discrepancy and continue from the verified repository state.
- `.local-state/` is local runtime data and must never be committed or uploaded as a project artifact.

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
- Local mobile/PWA readiness gate: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-mobile-readiness.ps1 -BaseUrl "http://127.0.0.1:3001" -AllowInsecureLocalhost`

## Project-specific safety rules

- API keys are server-side environment variables only. Never return key values from an API.
- Execution traces may expose event summaries, tool names, sources, status, and duration, but never raw private chain-of-thought.
- MCP and internal tools must be allowlisted, permission-checked, and auditable. Never execute model-supplied shell commands.
- Project plugins register metadata, context, tools, views, artifacts, and permissions through the project contract.
- General must remain a working project when the Soccer example plugin is absent.
- Public deployments must enable access protection or use an owner-only identity proxy; never expose the API anonymously.
- `NEXT_PUBLIC_PERSONAL_AI_OS_MOBILE_PREVIEW=true` is allowed only for an access-controlled, visibly labelled UI-only preview; never enable it for the functional deployment.
- V0.1 remains a modular monolith; do not introduce microservices, HealthKit, full calendar sync, or multi-user collaboration.
