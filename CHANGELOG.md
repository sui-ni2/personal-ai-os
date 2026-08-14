# Changelog

All notable changes to Personal AI OS are documented here.

This project follows Semantic Versioning for public releases.

## [0.1.0] - Unreleased

### Added

- A local-first Personal AI workspace with Next.js web UI and FastAPI/SQLite backend.
- Text chat and GPT Live conversation modes with restart-safe conversation history.
- OpenAI and Anthropic provider adapters behind one streaming interface.
- Server-side provider configuration, live connection checks, and persistent default provider/model selection.
- Standard and Advanced interface modes so ordinary workflows can hide technical controls while keeping self-hosted capabilities available.
- Project-scoped persistent state, version history, optimistic concurrency, locked/formal-state protection, workflow gates, and project-bound MCP continuity tools.
- Allowlisted MCP gateway with HTTP and fixed-command-alias stdio connectors.
- General, Soccer, and isolated P5 project plugins under a common project contract.
- P5 review-first workflow with immutable 10,000-candidate observation locks, diagnostic Top10/Top5 prefixes, lookup, evidence, conflict rejection, and audit views.
- Tenant-scoped core persistence and explicit community/cloud delivery contracts.
- Mobile PWA shell and documented HTTPS deployment path.

### Security and privacy

- Provider credentials remain server-side and are not returned by Settings.
- Private project runtime databases and project-specific data remain physically isolated.
- Execution/audit surfaces redact credentials, authorization data, cookies, tracebacks, and reasoning fields.
- MCP tools are allowlisted and models cannot submit arbitrary shell commands.
- Cloud mode fails closed until real account identity is available.

### Release gate

`v0.1.0` must not be published until the release checklist in `docs/release-checklist.md` passes, including a real-provider fresh-install smoke test. Until then this section remains `Unreleased`.
