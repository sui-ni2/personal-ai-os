# Project evidence ledger

This page records public evidence about Personal AI OS without treating repository activity as proof of independent adoption. Mutable metrics are dated, and external-use claims require a public source that can be inspected independently.

## Snapshot — 2026-08-18

### Project and maintenance evidence

- Public Apache-2.0 repository: `sui-ni2/personal-ai-os`.
- First stable tagged release: `v0.2.0`.
- Runnable local-first application with Chat, Projects, reviewed Memory, execution history, MCP tooling, OpenAI/Anthropic adapters, and optional local Ollama support; the runnable surface is documented in `README.md`.
- Repository CI covers backend tests, frontend checks/builds, platform readiness, CodeQL, and dependency review; repository-admin hardening is tracked in Issue #39.
- Executable maintainer helpers cover CI failure classification, dependency-update risk summaries, release-evidence verification, and external tester-feedback triage. Their fail-closed contracts and focused tests are documented in `docs/maintainer-automation.md`.
- PR #74 is a concrete dependency-maintenance example: Platform Readiness prevented two incomplete Dependabot upgrades from merging, the peer dependencies were aligned together, and the replacement passed CI, CodeQL, Dependency Review, hosted vinext readiness, Windows no-key readiness, and container/PWA readiness before merge.
- Public repository snapshot observed on 2026-08-18: **23 stars, 5 forks, and 4 open issues**. The four open issues are the external validation paths listed below; there are no open pull requests at this snapshot.

These are project-health and reach signals. They are **not** counted here as proof that an independent user successfully adopted the software.

### Independent adoption evidence

**No qualifying independent issue, pull request, or first-hand use report has been verified in this repository yet.**

The repository intentionally keeps this state explicit rather than converting maintainer activity, CI results, stars, forks, synthetic accounts, reciprocal engagement, bot pull requests, or generated testimonials into adoption claims.

When independent evidence exists, it should be added only with a direct public link and enough context to understand what was actually verified.

## Open validation paths

- Issue #7 — first run, first chat, and restart-persistence feedback.
- Issue #15 — Windows zero-cost fresh-install verification.
- Issue #55 — genuine real-world use or attempted use.
- Issue #56 — macOS/Linux Docker verification.
- `Real-world use` and `Early tester feedback` issue forms under `.github/ISSUE_TEMPLATE/`.

Negative results are valid evidence. A reproducible report explaining why setup or continued use failed is more useful than an unsupported positive claim.

## Evidence categories

| Category | What qualifies | Current state |
| --- | --- | --- |
| Release maturity | Public tagged release and runnable documented paths | Verified (`v0.2.0`) |
| Maintenance | CI/security/repository governance and tested maintainer workflows with public evidence | Verified |
| Reach | Stars/forks observed on a stated date | 23 stars / 5 forks on 2026-08-18 |
| Independent install | First-hand report from a non-maintainer with environment/version | None verified yet |
| Independent workflow use | First-hand real workflow report from a non-maintainer | None verified yet |
| External contribution | Non-maintainer issue/PR tied to genuine use or a focused improvement | None verified yet |
| Independent re-test | External confirmation after a reported fix | None verified yet |

## Update rules

1. Date every mutable metric snapshot.
2. Link every independent-adoption claim to the public issue, pull request, or comment that supports it.
3. Preserve negative and partial-use reports when they are good-faith and reproducible.
4. Keep maintainer dogfooding separate from independent adoption.
5. Do not count synthetic or duplicate accounts, paid/reciprocal engagement, coordinated stars/forks/comments, bot activity, or generated testimonials.
6. If evidence is ambiguous, record it as unverified rather than infer a positive result.

See `docs/real-world-use.md` for submission and privacy guidance.