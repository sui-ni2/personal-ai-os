# Maintainer evidence summary

**Observation date:** 2026-08-30

Personal AI OS is a local-first, provider-neutral workspace for long-running AI work. Its core premise is that project state — conversations, reviewed memory, tools, execution history, and project context — should remain under the user's control while model providers remain replaceable execution engines.

## What is runnable now

The public community edition includes a Next.js application shell, FastAPI API, SQLite persistence, provider adapters for OpenAI and Anthropic plus an optional local Ollama adapter, restart-safe conversation history, an allowlisted MCP gateway, auditable execution events, project plugins, and an installable PWA shell. The current stable release line is `v0.3.0`.

The repository also provides a zero-cost verification path that requires no paid provider key. That path verifies clean startup, the expected runtime version, unconfigured-provider behavior, and secret redaction without making a billable model call. See `docs/try-without-api.md`.

## Maintainer responsibilities evidenced in the repository

Public repository activity shows responsibility for:

- product architecture and boundary decisions;
- release preparation and version consistency;
- backend/frontend tests and build checks;
- CI, CodeQL, Dependency Review, Dependabot, and platform-readiness maintenance;
- security/privacy documentation and repository hardening;
- contributor and tester intake;
- issue triage and follow-up fixes.

Repository-admin hardening is tracked in Issue #39 and `docs/repository-admin-checklist.md`.

## Executable maintainer automation

The repository contains deterministic, tested helpers for recurring maintenance tasks:

- CI failure classification: `scripts/ci_failure_classifier.py`;
- dependency-update risk summary: `scripts/dependency_risk_summary.py`;
- release evidence verification: `scripts/release_evidence_verifier.py`;
- external tester feedback triage: `scripts/tester_feedback_triage.py`.
- CI evidence collection: `scripts/ci_evidence_collector.py`;
- release evidence assembly: `scripts/release_evidence_assembler.py`;
- tester feedback traceability: `scripts/tester_feedback_traceability.py`.

Focused tests for all four live in `apps/api/tests/`. These tools are fail-closed: they do not approve or merge pull requests, bypass required checks, create releases, or convert tester text into verified adoption. See `docs/maintainer-automation.md` for the command-line contracts and safety boundary.

## Release, security, and CI evidence

The repository has a `v0.2.0` tag but, as of the observation date, **no GitHub Release**. Normal pull requests run backend and frontend checks; CodeQL analyzes Python and JavaScript/TypeScript; Dependency Review fails closed on newly introduced high-severity dependency risk; Platform Readiness exercises the documented first-run paths; release candidates have an isolated provider-smoke gate. The current v0.3.0 candidate is not release-ready until all five required gates attach to the same fresh frozen SHA.

The latest observed `main` commit includes merged dependency maintenance from PRs #77 and #78, and the latest observed scheduled CodeQL run on that commit completed successfully.

The project keeps secrets server-side, redacts secret-bearing audit fields, restricts MCP tool execution through allowlists, and documents private vulnerability reporting and privacy boundaries.

## Independent adoption evidence

Independent adoption is intentionally reported separately from maintainer activity and repository reach metrics.

As of 2026-08-30, the repository has **59 stars and 14 forks**, but those remain reach signals rather than proof of successful use. `INDEPENDENT_ADOPTION_VERIFIED = 0`; the public evidence ledger does **not** claim a qualifying independent installation report, real-world-use report, or external pull request.

External interest has appeared in Issues #55 and #56, but expressions of interest without an environment-and-result report or a concrete external contribution are kept unverified. This distinction is deliberate.

See `docs/evidence-ledger.md`, `docs/real-world-use.md`, and `docs/support-matrix.md` for the current evidence state.

## Current evidence gaps

The most important remaining gaps are external rather than architectural:

1. an independent fresh-install report with OS/runtime details and an explicit result;
2. an independent real workflow report, including failed or partial adoption;
3. an external bug fix, documentation fix, or focused pull request;
4. independent verification of Windows and macOS/Linux setup paths;
5. provider-backed first-chat and restart-persistence verification by a tester using their own supported provider configuration.

These gaps must be closed by genuine third-party activity. Maintainer-authored testimonials, synthetic accounts, reciprocal engagement, paid stars/forks/comments, or generated feedback must not be used as substitutes.
