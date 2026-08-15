# Personal AI OS v0.2.0 — Release Notes Draft

> **Draft only. Do not publish this as a GitHub Release until every item in `docs/release-checklist.md` passes.**

Personal AI OS is a user-controlled, local-first AI workspace for long-running projects. The `v0.2.0` stable line focuses on making the current community/self-hosted edition usable, auditable, and safe enough for genuine early-user testing while preserving fail-closed boundaries for future managed-cloud delivery.

## Highlights

- Next.js web workspace with Chat, Memory, Repository, Projects, and Settings.
- Text chat and GPT Live conversation modes with restart-safe conversation history.
- OpenAI and Anthropic adapters behind one provider-independent streaming interface.
- Server-side credential handling, connection checks, and persistent default provider/model selection.
- Standard and Advanced interface modes.
- Project-scoped persistent state, version history, workflow gates, and project-bound MCP continuity tools.
- Allowlisted MCP gateway supporting HTTP and fixed-command-alias stdio connectors.
- General, Soccer, and isolated P5 project plugins under one project contract.
- Tenant-scoped core persistence and explicit community/cloud product boundaries.
- Installable mobile PWA shell and documented HTTPS deployment path.

## Security and privacy

- Provider credentials stay server-side and are not returned by Settings.
- Runtime databases, private conversations, logs, uploads, backups, and private project data are not part of the public source distribution.
- Audit surfaces redact credentials, authorization data, cookies, tracebacks, and reasoning fields.
- MCP tools are allowlisted; models cannot submit arbitrary shell commands.
- Cloud mode fails closed until real account identity is available.

## Known limitations

- The current runnable distribution is the community/self-hosted edition.
- Cloud accounts, billing, managed provider routing, and device sync are not yet live.
- Provider calls require user-supplied server-side credentials.
- GPT Live and phone installation require a trusted HTTPS deployment for real-device use.
- The stable release must not be published until the real-provider fresh-install smoke test and final privacy/artifact audit pass.

## Verification before publication

See `docs/release-checklist.md`. Required release evidence includes clean-checkout automated checks, an isolated real-provider fresh-install test, restart/persistence verification, and a final no-secrets/private-artifacts audit.

## Feedback

Early users should report sanitized fresh-install and first-chat feedback in Issue #7. Never include API keys, `.env` files, authorization headers, cookies, private conversations, runtime databases, or secret-bearing logs in public reports.