# Changelog

All notable changes to Personal AI OS are documented here.

This project follows Semantic Versioning for public releases.

## [0.2.0] - 2026-08-15

This stable release continues the version line established by the historical `v0.2.0-alpha.1` tag. That alpha tag remains part of repository history; no GitHub Release was published for it.

### Added

- A local-first, provider-neutral Personal AI workspace with Next.js web UI and FastAPI/SQLite backend.
- Text chat and GPT Live conversation modes with restart-safe conversation history.
- OpenAI, Anthropic, and optional local Ollama provider adapters behind one streaming interface.
- Server-side provider configuration, live connection checks, and persistent default provider/model selection.
- Standard and Advanced interface modes so ordinary workflows can hide technical controls while keeping self-hosted capabilities available.
- Project-scoped persistent state, version history, optimistic concurrency, locked/formal-state protection, workflow gates, and project-bound MCP continuity tools.
- Allowlisted MCP gateway with HTTP and fixed-command-alias stdio connectors.
- General, Soccer, and isolated P5 project plugins under a common project contract.
- P5 review-first workflow with immutable 10,000-candidate observation locks, diagnostic Top10/Top5 prefixes, lookup, evidence, conflict rejection, and audit views.
- Tenant-scoped core persistence and explicit community/cloud delivery contracts.
- Mobile PWA shell and documented HTTPS deployment path.
- An isolated release workflow that performs real model inference with a pinned local Ollama runtime when no maintainer-owned remote provider secret is available.

### Security and privacy

- Provider credentials remain server-side and are not returned by Settings.
- Ollama is disabled by default and must be explicitly enabled before the application treats it as configured.
- Private project runtime databases and project-specific data remain physically isolated.
- Execution/audit surfaces redact credentials, authorization data, cookies, tracebacks, and reasoning fields.
- MCP tools are allowlisted and models cannot submit arbitrary shell commands.
- Cloud mode fails closed until real account identity is available.
- CI, CodeQL, Dependency Review, Platform Readiness, and a real-inference release gate form the repository release-safety baseline.

### Release verification

The `v0.2.0` release candidate is gated by `docs/release-checklist.md`. The final verified commit must pass the complete application-level real-inference loop—including provider connection, one text-chat turn, restart, and continued persisted conversation state—plus the normal CI/security/platform checks before the tag and GitHub Release are created.
