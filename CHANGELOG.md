# Changelog

All notable changes to Personal AI OS are documented here.

This project follows Semantic Versioning for public releases.

## [Unreleased]

### Added

- A guarded one-command Windows first-run bootstrap that validates Python/Node/pnpm prerequisites, preserves existing local configuration, installs repository dependencies, and runs the no-key readiness gate without a billable provider model call.
- A localhost-only Docker Compose first-run path with a named persistent data volume and optional host Ollama connectivity.
- Bounded compact/full project handoff snapshots backed by the existing project-scoped continuity stores, with explicit record limits, truncation reporting, project isolation, and deliberate exclusion of state history, workflow transition evidence, provider sessions, and credentials.
- An explicit Projects-screen continuity preview that loads compact handoff data only after a user action, requires a second explicit action for full details, previews snapshots before clipboard copy, and does not persist a second client-side handoff copy.
- Deterministic maintainer helpers for CI-failure classification, dependency-risk summaries, release-evidence verification, and external tester-feedback triage, with focused fail-closed tests.
- Public evidence/support documentation and issue forms that separate repository reach, maintainer activity, genuine external validation, and real-world-use reports instead of treating them as interchangeable adoption signals.
- A GitHub Release publishing workflow that validates stable tags reachable from `main` before publishing a missing release.
- A private security-reporting entry in the GitHub issue chooser so vulnerability details are routed away from public issues.
- Tenant-scoped generic Project creation for provider-neutral long-running research or build work, without adding domain-specific core fields.
- Explicit crash/restart recovery metadata and user-confirmed project recovery from bounded persisted state; it never copies provider sessions, chat history, transition receipts, or private reasoning.
- Deterministic CI evidence collection, release-evidence assembly, and tester-feedback traceability around the existing fail-closed classifier/verifier gates.

### Security and maintenance

- The default branch is protected by an active repository ruleset requiring pull requests, independent CI/CodeQL/Dependency Review checks, resolved review conversations, and blocking force pushes and deletion.
- GitHub private vulnerability reporting is enabled and `SECURITY.md` directs sensitive reports to the private flow.
- Platform Readiness now exercises both the Windows bootstrap and Docker Compose startup paths end to end, including health and mobile/PWA verification.
- Contributor, support, and tester documentation now exposes distinct Windows, macOS/Linux Docker, provider-backed first-chat/restart, and genuine real-world-use validation paths while retaining a manual source setup for advanced contributors.
- Public maintainer/evidence claims are kept aligned with verifiable repository state; expressions of interest, stars, forks, CI, and maintainer-authored activity are not promoted to verified third-party adoption.
- Project handoff remains protected by the existing application access boundary and physically isolated per-project state stores; the UI does not fetch handoff data during ordinary Projects page load.

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

The `v0.2.0` tag was gated by `docs/release-checklist.md`. A live GitHub Releases query on 2026-08-30 found no published GitHub Release, so this changelog does not claim GitHub Release publication, release notes, or assets for the tag.
