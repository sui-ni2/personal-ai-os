# Personal AI OS v0.2.0 — Release Notes Draft

> **Draft only. Do not publish this as a GitHub Release until every item in `docs/release-checklist.md` passes.**

Personal AI OS is a local-first, provider-neutral workspace for long-running AI work. Projects, context, reviewed memory, tools, and auditable execution belong to the workspace rather than to any one model provider. The `v0.2.0` stable line turns that product contract into a usable community/self-hosted release while keeping future managed-cloud account and billing boundaries fail-closed.

## Highlights

- Next.js web workspace with Chat, Memory, Repository, Projects, and Settings.
- Text chat and GPT Live conversation modes with restart-safe conversation history.
- OpenAI, Anthropic, and GitHub Models adapters behind one provider-independent streaming interface.
- Server-side credential handling, live connection checks, and persistent default provider/model selection.
- Standard and Advanced interface modes so routine use can stay simple without removing self-hosted controls.
- Project-scoped persistent state, version history, workflow gates, and project-bound MCP continuity tools.
- Allowlisted MCP gateway supporting HTTP and fixed-command-alias stdio connectors.
- General, Soccer, and isolated P5 project plugins under one project contract.
- Tenant-scoped core persistence and explicit community/cloud product boundaries.
- Installable mobile PWA shell and documented HTTPS deployment path.
- CI, CodeQL, Dependency Review, Windows/container Platform Readiness, and an isolated real-provider release smoke gate.

## Provider-neutral release verification

The release candidate adds GitHub Models as a real third provider rather than as a test stub. Release-branch pull requests can use the workflow-scoped GitHub Actions token with read-only Models permission to perform a real remote inference smoke test. The runner verifies no-key startup, secret redaction, provider connection, model selection persistence, a real text-chat turn, API restart, and continued conversation state in an isolated temporary runtime.

The token and model response text are not printed or attached as release evidence. A failed or skipped real-provider workflow is not treated as a pass.

## Security and privacy

- Provider credentials stay server-side and are not returned by Settings.
- Runtime databases, private conversations, logs, uploads, backups, and private project data are not part of the public source distribution.
- Audit surfaces redact credentials, authorization data, cookies, tracebacks, and reasoning fields.
- MCP tools are allowlisted; models cannot submit arbitrary shell commands.
- Cloud mode fails closed until real account identity is available.
- GitHub Models release verification uses an ephemeral workflow token with least-required `models: read` permission rather than a persisted maintainer credential when no OpenAI/Anthropic repository secret is configured.

## Known limitations

- The current runnable distribution is the community/self-hosted edition.
- Cloud accounts, billing, managed provider routing, and device sync are not yet live.
- Local provider calls require a user-supplied server-side OpenAI, Anthropic, or GitHub Models credential.
- GPT Live and phone installation require a trusted HTTPS deployment for real-device use.
- `v0.2.0` must not be published until the real-provider fresh-install workflow and final privacy/artifact audit pass.

## Verification before publication

See `docs/release-checklist.md`. Required release evidence includes clean-checkout automated checks, an isolated real-provider fresh-install test, restart/persistence verification, and a final no-secrets/private-artifacts audit.

## Feedback

Early users should report sanitized fresh-install and first-chat feedback in Issue #7. Never include API keys, GitHub tokens, `.env` files, authorization headers, cookies, private conversations, runtime databases, or secret-bearing logs in public reports.
