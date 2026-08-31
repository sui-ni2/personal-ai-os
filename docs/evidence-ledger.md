# Project evidence ledger

This page records public evidence about Personal AI OS without treating repository activity as proof of independent adoption. Mutable metrics are dated, and external-use claims require a public source that can be inspected independently.

## Snapshot — 2026-08-31

## Reach

- Public repository snapshot observed on 2026-08-31: **59 stars, 14 forks, and 2 subscribers/watchers**.
- These are public reach signals only. They are not independent-adoption evidence.

## Maintenance

- Public Apache-2.0 repository: `sui-ni2/personal-ai-os`.
- First stable tagged release: `v0.2.0` at `934efa959d2487c6942951d90bb543b4104369f6`. A live GitHub Releases query returned **zero releases** on 2026-08-30, so this repository does not claim a published v0.2.0 GitHub Release, release notes, or release assets.
- Stable `v0.3.0` is an annotated tag resolving to `8e14e857ffbae642268ea069c9b9d1f0c72f5cdd` and has a published [GitHub Release](https://github.com/sui-ni2/personal-ai-os/releases/tag/v0.3.0). PR #90 merged its release preparation to `main` as `e5275ef24d5154974c324121db41bb870bac049c` after five exact-SHA gates and a `ready_to_tag` verifier result.
- Runnable local-first application with Chat, Projects, reviewed Memory, execution history, MCP tooling, OpenAI/Anthropic adapters, and optional local Ollama support; the runnable surface is documented in `README.md`.
- Repository CI covers backend tests, frontend checks/builds, platform readiness, CodeQL, and dependency review; repository-admin hardening is tracked in Issue #39.
- Executable maintainer helpers cover CI failure classification, dependency-update risk summaries, release-evidence verification, and external tester-feedback triage. Their fail-closed contracts and focused tests are documented in `docs/maintainer-automation.md`.
- PR #74 remains a concrete dependency-maintenance example: Platform Readiness prevented two incomplete Dependabot upgrades from merging, the peer dependencies were aligned together, and the replacement passed the repository's required verification before merge.
- Current `main` includes the merged dependency maintenance from PRs #77 and #78. The latest observed scheduled CodeQL run on that `main` commit completed successfully.
- Dependabot alert #3 (`GHSA-2v37-7h3g-55p8` / `CVE-2026-67213`) was remediated by PR #89 and is recorded by GitHub as fixed on 2026-08-31; there are no open high-severity Dependabot alerts in this snapshot.
- Four open issues are the external validation paths listed below; there are no open pull requests at this snapshot.

These are project-health and reach signals. They are **not** counted here as proof that an independent user successfully adopted the software.

## Independent adoption

**INDEPENDENT_ADOPTION_VERIFIED = 0.** No qualifying independent installation report, real-world-use report, or external pull request has been verified in this repository yet.

There is genuine external interest, but the evidence boundary remains strict:

- Issue #56 contains a non-maintainer comment volunteering to test the macOS/Linux Docker path, but no environment-and-result report has been posted yet, so it is not counted as an independent install verification.
- Issue #55 contains a non-maintainer request to contribute, but it does not describe actual Personal AI OS use; the maintainer redirected that person to concrete reproducible verification tasks rather than counting the comment as adoption evidence.

The repository intentionally keeps this state explicit rather than converting maintainer activity, CI results, stars, forks, expressions of interest, synthetic accounts, reciprocal engagement, bot pull requests, or generated testimonials into adoption claims.

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
| Release maturity | Public tagged release and runnable documented paths | Verified (`v0.2.0`, `v0.3.0`) |
| Maintenance | CI/security/repository governance and tested maintainer workflows with public evidence | Verified |
| Reach | Stars/forks observed on a stated date | 59 stars / 14 forks on 2026-08-31 |
| Independent install | First-hand report from a non-maintainer with environment/version and result | None verified yet |
| Independent workflow use | First-hand real workflow report from a non-maintainer | None verified yet |
| External contribution | Non-maintainer issue/PR tied to genuine use or a focused improvement | None verified yet |
| Independent re-test | External confirmation after a reported fix | None verified yet |

## Update rules

1. Date every mutable metric snapshot.
2. Link every independent-adoption claim to the public issue, pull request, or comment that supports it.
3. Preserve negative and partial-use reports when they are good-faith and reproducible.
4. Keep maintainer dogfooding separate from independent adoption.
5. Do not count synthetic or duplicate accounts, paid/reciprocal engagement, coordinated stars/forks/comments, bot activity, expressions of intent without results, or generated testimonials.
6. If evidence is ambiguous, record it as unverified rather than infer a positive result.

See `docs/real-world-use.md` for submission and privacy guidance.
