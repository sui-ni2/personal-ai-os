# Codex for Open Source reviewer packet — 2026-10-22

This page is a compact index of public, independently inspectable repository evidence for a maintainer review. It is not an approval claim and it does not convert repository popularity into user adoption.

## Project

- Repository: [sui-ni2/personal-ai-os](https://github.com/sui-ni2/personal-ai-os)
- License: Apache-2.0.
- Current stable release line: `v0.3.0`.
- Product boundary: local-first, provider-neutral workspace for durable project state, reviewed memory, tools, and auditable execution.
- Application evidence baseline: `4022c2411a622c58deab4271823f3b1fcc9b1a31` (PR #142), which refreshed the dated evidence ledger and maintainer summary.

## Maintainer responsibilities with public evidence

The primary maintainer, @sui-ni2, is responsible for roadmap decisions, issue triage, pull-request review and merge decisions, release management, dependency/security maintenance, and keeping project claims aligned with inspectable evidence. See [MAINTAINERS.md](../MAINTAINERS.md).

Concrete recent examples:

- [PR #133](https://github.com/sui-ni2/personal-ai-os/pull/133): non-maintainer @yunaremaia identified and fixed incorrect project-context truncation reporting; contributor authorship was preserved on merge after review and required checks.
- [PR #140](https://github.com/sui-ni2/personal-ai-os/pull/140): maintainer follow-through on the analogous workflow-context issue surfaced during review of #133.
- [PR #141](https://github.com/sui-ni2/personal-ai-os/pull/141): coordinated Vite/vinext security and compatibility maintenance without weakening supply-chain controls.
- [PR #142](https://github.com/sui-ni2/personal-ai-os/pull/142): evidence refresh after CI, CodeQL, Dependency Review, and hardening checks.

Repository workflows cover normal CI, CodeQL, Dependency Review, platform readiness, and release/provider gates. The project also contains deterministic maintainer helpers for CI failure classification, dependency-risk review, release-evidence verification, and tester-feedback traceability.

## External open-source contribution evidence

The repository has a verified non-maintainer code contribution through PR #133. The project records this as contributor/community evidence, not as proof of successful end-user adoption.

The maintainer also contributes upstream to [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp):

- [FastMCP PR #4849](https://github.com/PrefectHQ/fastmcp/pull/4849) — merged: reject non-positive upstream token expiry.
- [FastMCP PR #4861](https://github.com/PrefectHQ/fastmcp/pull/4861) — merged: cache OIDC discovery configuration with bounded TTL and caller isolation.
- [FastMCP PR #4881](https://github.com/PrefectHQ/fastmcp/pull/4881) — open and mergeable at the 2026-10-22 observation; exact-head tests, static analysis, and downstream smoke are recorded as successful in the PR, with maintainer review/approval still outstanding.

These upstream contributions are separate from Personal AI OS adoption and are included only as evidence of sustained open-source maintenance work.

## Runnable and reviewable paths

A reviewer can inspect or exercise the project without a paid provider key:

- [5-minute evaluation](5-minute-evaluation.md)
- [Try without an API key](try-without-api.md)
- [External test packet](external-test-packet.md)
- [Verification support matrix](support-matrix.md)
- [Application readiness audit](application-readiness-audit.md)
- [Project evidence ledger](evidence-ledger.md)
- [Maintainer evidence summary](maintainer-evidence-summary.md)

The no-key path verifies startup, expected runtime state, unconfigured-provider behavior, and secret redaction. It does not claim a real model response without a configured provider.

## Evidence boundary

As of this packet:

- `INDEPENDENT_ADOPTION_VERIFIED = 0`.
- Stars, forks, commit count, CI, maintainer dogfooding, bot activity, and expressions of intent are not treated as successful independent adoption.
- The merged external PR is real contributor evidence, but is not promoted into end-user adoption without a first-hand usage result.
- Open validation paths remain Issues [#7](https://github.com/sui-ni2/personal-ai-os/issues/7), [#15](https://github.com/sui-ni2/personal-ai-os/issues/15), [#55](https://github.com/sui-ni2/personal-ai-os/issues/55), and [#56](https://github.com/sui-ni2/personal-ai-os/issues/56).

Negative and partial external results are valid evidence. The repository explicitly rejects synthetic testimonials, duplicate accounts, reciprocal engagement, paid stars/forks/comments, and generated feedback.

## What support would be used for

If selected for Codex for Open Source support, project-scoped API/Codex capacity would be used for open-source maintainer workflows such as reproducible pull-request review, regression-test generation, issue triage, release-readiness checks, security-focused code review, and validation of OpenAI-provider integrations. It would not be represented as proof of adoption or approval.
