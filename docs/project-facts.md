# Project facts and verification map

This page is a compact map of claims that reviewers, users, and contributors can verify directly in the repository. It intentionally separates **maintainer/engineering evidence** from **independent adoption evidence**.

## Project identity

- Personal AI OS is an open-source, local-first, provider-neutral workspace for long-running AI work.
- The repository is licensed under Apache-2.0.
- The documented current stable line is `v0.3.x`; the README identifies `v0.3.0` as the current stable tagged release. `v0.2.0` remains historical release evidence.
- The community edition is runnable locally. Managed-cloud accounts, billing, and device sync remain outside the currently live product boundary.

Primary sources: [`README.md`](../README.md), [`LICENSE`](../LICENSE), and [`docs/product-contract.md`](product-contract.md).

## Runnable verification

A reviewer can verify the product without relying on screenshots or maintainer-only infrastructure:

- **Zero-cost Docker path:** `docker compose up --build -d`, then open `http://127.0.0.1:8080`.
- **Windows source bootstrap:** `scripts/setup-windows.ps1` validates prerequisites and runs the no-key readiness gate.
- **No-key smoke:** `scripts/release-provider-smoke.py --provider openai --no-key-only` checks safe startup, unconfigured-provider behavior, and secret redaction without making a billable model call.
- **Provider path:** Issue #7 defines the external provider → first chat → restart-persistence verification flow.
- **Independent platform verification:** Issue #15 covers a Windows fresh install and Issue #56 covers macOS/Linux Docker verification.

Primary sources: [`README.md`](../README.md), [`docs/try-without-api.md`](try-without-api.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md), [Issue #7](https://github.com/sui-ni2/personal-ai-os/issues/7), [Issue #15](https://github.com/sui-ni2/personal-ai-os/issues/15), and [Issue #56](https://github.com/sui-ni2/personal-ai-os/issues/56).

## Implemented product surface

The repository currently contains runnable implementations for:

- Chat, Projects, reviewed Memory, Repository, and Settings surfaces;
- restart-safe conversation and project persistence;
- OpenAI and Anthropic remote adapters plus explicitly enabled local Ollama;
- an allowlisted MCP gateway with HTTP and fixed-command-alias stdio connectors;
- auditable execution events and bounded/redacted tool results;
- an installable PWA shell and server-mediated GPT Live path;
- isolated project plugins that use the shared project contract rather than adding domain fields to the core schemas.

These are engineering claims. They can be checked in source, tests, and the runnable application; they are **not** presented as proof of external adoption.

## Maintenance and security evidence

Normal repository maintenance includes:

- backend tests and Python compilation;
- frontend type checking and production builds;
- the no-key readiness gate;
- Platform Readiness checks;
- CodeQL analysis;
- Dependency Review;
- Dependabot dependency monitoring.

Automated checks, maintainer commits, release tags, and repository settings demonstrate maintenance discipline. They do not by themselves demonstrate meaningful third-party use.

Primary sources: [`.github/workflows`](../.github/workflows), [`docs/repository-admin-checklist.md`](repository-admin-checklist.md), and the repository Actions history.

## Independent use and contribution evidence

Independent adoption is tracked separately and conservatively:

- Issue #55 asks external users to report a genuine workflow, including failed or partial adoption.
- The `Real-world use` issue form records environment, version, workflow, outcome, and the highest-value next change.
- [`docs/real-world-use.md`](real-world-use.md) defines what counts and explicitly excludes maintainer-authored testimonials, synthetic/duplicate accounts, reciprocal engagement, paid activity, generated testimonials, and CI activity from adoption evidence.
- External bug reports, focused pull requests, and independent re-tests of fixes are stronger evidence than raw engagement counts because they are tied to observable use.

Primary sources: [Issue #55](https://github.com/sui-ni2/personal-ai-os/issues/55), [Issue #56](https://github.com/sui-ni2/personal-ai-os/issues/56), [`.github/ISSUE_TEMPLATE/real_world_use.yml`](../.github/ISSUE_TEMPLATE/real_world_use.yml), and [`docs/real-world-use.md`](real-world-use.md).

## Evidence rule

When describing the project externally, use only claims that can be linked to public repository evidence or clearly identified first-party dogfooding. Do not convert stars, forks, CI runs, maintainer activity, or synthetic feedback into claims of real-world adoption.
