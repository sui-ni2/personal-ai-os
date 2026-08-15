# Personal AI OS v0.2.0 — Release Notes Draft

> **Draft only. Do not publish this as a GitHub Release until every item in `docs/release-checklist.md` passes.**

Personal AI OS is a local-first, provider-neutral workspace for long-running AI work. Projects, context, reviewed memory, tools, and auditable execution belong to the workspace rather than to any one model provider. The `v0.2.0` stable line turns that product contract into a usable community/self-hosted release while keeping future managed-cloud account and billing boundaries fail-closed.

## Highlights

- Next.js web workspace with Chat, Memory, Repository, Projects, and Settings.
- Text chat and GPT Live conversation modes with restart-safe conversation history.
- OpenAI, Anthropic, and optional local Ollama adapters behind one provider-independent streaming interface.
- Server-side credential handling for remote providers, explicit local-provider enablement, live connection checks, and persistent default provider/model selection.
- Standard and Advanced interface modes so routine use can stay simple without removing self-hosted controls.
- Project-scoped persistent state, version history, workflow gates, and project-bound MCP continuity tools.
- Allowlisted MCP gateway supporting HTTP and fixed-command-alias stdio connectors.
- General, Soccer, and isolated P5 project plugins under one project contract.
- Tenant-scoped core persistence and explicit community/cloud product boundaries.
- Installable mobile PWA shell and documented HTTPS deployment path.
- CI, CodeQL, Dependency Review, Windows/container Platform Readiness, and an isolated real-inference release gate.

## Real-inference release verification

The final release candidate can verify the provider-independent application path without requiring a maintainer-owned paid API credential. If no OpenAI or Anthropic release secret is configured, the release workflow installs a pinned local Ollama runtime on the isolated runner, pulls a small allowlisted model, and exercises the same application provider boundary used by normal chat.

The smoke runner verifies fresh no-provider startup, secret redaction, live provider connection, persisted provider/model selection, a real text-chat turn, API restart, and continued conversation state. Model response text is not printed or attached as release evidence. A failed or skipped real-inference workflow is not treated as a pass.

## Security and privacy

- Remote provider credentials stay server-side and are not returned by Settings.
- Ollama is disabled by default and must be explicitly enabled before it is treated as configured.
- Runtime databases, private conversations, logs, uploads, backups, and private project data are not part of the public source distribution.
- Audit surfaces redact credentials, authorization data, cookies, tracebacks, and reasoning fields.
- MCP tools are allowlisted; models cannot submit arbitrary shell commands.
- Cloud mode fails closed until real account identity is available.

## Known limitations

- The current runnable distribution is the community/self-hosted edition.
- Cloud accounts, billing, managed provider routing, and device sync are not yet live.
- OpenAI and Anthropic require user-supplied server-side credentials; Ollama requires a separately running local service and explicit enablement.
- GPT Live and phone installation require a trusted HTTPS deployment for real-device use.
- `v0.2.0` must not be published until the real-inference fresh-install workflow and final privacy/artifact audit pass.

## Verification before publication

See `docs/release-checklist.md`. Required release evidence includes clean-checkout automated checks, an isolated real-inference fresh-install test, restart/persistence verification, and a final no-secrets/private-artifacts audit.

## Feedback

Early users should report sanitized fresh-install and first-chat feedback in Issue #7. Never include API keys, `.env` files, authorization headers, cookies, private conversations, runtime databases, or secret-bearing logs in public reports.
