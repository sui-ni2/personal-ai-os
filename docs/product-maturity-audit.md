# Product maturity audit

**Audit date:** 2026-08-31
**Audited baseline:** `origin/main` at `0c509d1` (`v0.3.0-3-g0c509d1`)
**Scope:** the single Personal AI OS community/self-hosted product. This is a
source-and-test-surface audit; the in-app visual audit is blocked because the
Codex in-app browser bridge was unavailable, so no screenshot-only UX claim is
made here.

## Status legend

Only these values are used below: `DONE`, `PARTIAL`, `MISSING`,
`BLOCKED_EXTERNAL`, and `NOT_NEEDED`.

| Product closure | Status | Evidence and bounded gap |
| --- | --- | --- |
| v0.3.0 release and Project Continuity recovery | DONE | `v0.3.0` is tagged; current `main` includes the explicit state/history/recovery implementation and release-evidence merge. This work must not be restarted. |
| Local-first FastAPI, Next.js, SQLite, tenant scope, provider adapters, MCP allowlist | DONE | Product contract, architecture, runtime, and existing regression suites agree on this core boundary. |
| Clean Windows source bootstrap and no-key startup | PARTIAL | `scripts/setup-windows.ps1` safely preserves `.env`/`.venv` and Platform Readiness covers it, but it still requires Python, Node and pnpm and is not a distributable install/update/rollback flow. |
| Backup, restore, and transfer package | PARTIAL | SQLite online backup, path-safe restore, and a secret-excluding transfer package exist. Version compatibility, package verification, transactional update, and user-facing rollback are absent. |
| Signed Windows artifacts | BLOCKED_EXTERNAL | Signing identity and certificate custody are not in this repository. A pipeline may be made signing-ready, but no artifact can honestly be called signed here. |
| Project Control Center | PARTIAL | Persistent Tasks/Decisions/Outcomes/Experience, handoff, and recovery APIs exist. The Projects UI is still a grid of entries rather than one compact, authoritative project home. |
| Settings center | PARTIAL | Provider/model configuration, MCP, voice/readiness and diagnostics fragments exist; settings are credential-blind. The requested user-facing grouping, project/global separation, privacy, data, budget and activity receipts are incomplete. |
| Privacy and audit redaction | DONE | Secrets stay server-side; tool-result audit payloads are bounded/redacted and historical rows are sanitized on read. |
| Send-scope receipt | MISSING | Chat builds project/workflow context but does not provide the user an itemized, persisted answer to “what left this workspace?”. |
| Usage ledger and enforceable budget | MISSING | There is no tenant/project/provider/model ledger or explicit hard-stop policy. |
| Side-effect confirmation | MISSING | MCP remains allowlisted, but external actions have no preview/confirm/receipt transaction. |
| Execution recovery | PARTIAL | Project restart recovery is explicit and conservative. Per-execution status, ambiguous side-effect handling, and safe-resume semantics are not persisted. |
| Provider conformance and fallback | PARTIAL | Adapters have streaming, cancellation, timeout, retry and model allowlist behavior. Routing policy, eligibility, user confirmation, fallback receipt, and cross-provider acceptance are missing. |
| Reviewed-memory governance | PARTIAL | Memory is tenant/project scoped and separate from Outcomes. It only has active/inactive lifecycle controls; proposal/review, provenance, conflict review, expiry/supersession, and usage receipts are missing. |
| Doctor diagnostics | MISSING | Health is present, but no redacted diagnostic command combines runtime, migrations, data, provider state, ports, storage and recovery checks. |
| Mobile/PWA and accessibility | PARTIAL | PWA shell and readiness checks exist. A live, screenshot-supported accessibility/mobile-flow audit remains blocked by the unavailable browser surface and physical-device testing. |
| CI, CodeQL, dependency review and platform/provider smoke | DONE | Workflows are present and the v0.3.0 evidence package records the completed release gates. New maturity work still needs its own local and CI evidence. |
| Managed cloud identity, billing and device sync | NOT_NEEDED | The product contract correctly keeps cloud fail-closed; this local-first closure must not claim those services. |

## Root causes

1. The release established a reliable substrate, but its product surfaces still
   expose component-level capabilities rather than a single continuity-first
   control plane.
2. The original safety model protects credentials and redacts traces, but it
   has no persisted intent/receipt model for context sending, non-idempotent
   actions, routing, or budgets.
3. Windows support is a carefully guarded developer/bootstrap path, not yet a
   versioned application distribution with a transactional update boundary.
4. Several public documents still call `v0.2.0` the current stable line even
   though `v0.3.0` is released. Historical v0.2 evidence remains historical;
   only current-tense assertions need correction.

## Audit constraints

- No `.env`, credentials, databases, conversations, backups, or user runtime
  data were opened or modified.
- No external-provider claim is inferred from local code. Mock contract tests
  are not real-provider validation.
- The in-app browser bridge was unavailable during this audit; visual and
  assistive-technology acceptance remain a named verification gap.
