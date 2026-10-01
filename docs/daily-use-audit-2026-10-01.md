# Daily-use audit — 2026-10-01

**Starting main:** `5114c2c8b8aa7aabf1b8701f0485e7b9a2c6b25f`, including merged
[PR #128](https://github.com/sui-ni2/personal-ai-os/pull/128). This audit supplements the
dated evidence snapshots; it does not replace earlier records or claim a v0.4 release.

## Current repository evidence

| Item | Observed result and scope |
| --- | --- |
| Main CI | [PASS](https://github.com/sui-ni2/personal-ai-os/actions/runs/36843571692) for the starting main SHA. |
| Main CodeQL | [PASS](https://github.com/sui-ni2/personal-ai-os/actions/runs/36843571691) for that SHA; live open Code Scanning alert count was 0. |
| Dependency Review | [PASS](https://github.com/sui-ni2/personal-ai-os/actions/runs/36843114786) for #128 head `ff286f50e43df41bdff8f283c4f919961b73c711`. This PR-diff gate is not a whole-lockfile vulnerability audit. |
| v0.4 Hardening | [PASS](https://github.com/sui-ni2/personal-ai-os/actions/runs/36843114610) for #128 head, including migration/governance/privacy/recovery, Windows artifact contracts, and Chromium/accessibility. The workflow does not run automatically on main pushes. |
| Platform Readiness | Latest applicable main [PASS](https://github.com/sui-ni2/personal-ai-os/actions/runs/36509094859) is `80778e680c14cbe5ed4b4d3d55b893eaecb25139`. #128 changed docs only and did not trigger this path-filtered workflow; there is no new platform result for `5114c2c`. |
| Required rules | Backend, frontend, both CodeQL language analyses, and Dependency Review; PR required and review threads must be resolved. Broader platform/hardening gates remain relevant even when not ruleset-required. |
| Release | [v0.3.0](https://github.com/sui-ni2/personal-ai-os/releases/tag/v0.3.0) remains the latest published stable release. v0.4 remains readiness work. |
| Open PRs at audit start | Dependabot #123 and #126 had successful applicable checks; #124 and #127 failed Hosted vinext build with incompatible React/React DOM versions. Do not merge those failed candidates or infer compatibility from other green checks. |
| Dependencies | Whole-lockfile `pnpm audit --json`: 2 high, 5 moderate, 3 low, 0 critical, all Undici through development-only Cloudflare/Miniflare tooling. `pnpm audit --prod --json`: 0 advisories. #126 still resolves affected Undici 7.29.0. |

## Daily-use evidence boundaries

The local checks in this repair branch used isolated, non-sensitive fixtures. They passed the
full non-live-provider backend suite, compilation, the no-key runtime smoke, `pip check`, and
Windows bootstrap `-CheckOnly`. No provider key or existing user data was accessed.

| Surface | Implemented / verified scope | Remaining real-use proof |
| --- | --- | --- |
| Projects, Tasks, Decisions, Outcomes, Continuity | API persistence, project/tenant isolation, handoff, control center, recovery and state-growth tests passed locally; #128's browser gate is separately linked above. | Independent daily workflow remains unverified. |
| Reviewed Memory | Proposal/review/conflict/acceptance and scoped-context tests passed. Private project experiences in handoff are a separate store from governed core Memory. | A multi-day user workflow across both stores is not established by fixtures. |
| Provider switching and Settings | Selection/persistence, deterministic routing/fault/fallback, Settings export/erase and redaction tests passed. | Real OpenAI/Anthropic switching: `BLOCKED_EXTERNAL` pending operator-configured credentials and a chosen live run. Existing local-provider receipts do not prove cross-provider switching. |
| Usage / budget ledger | Reservation, settlement, concurrent hard-stop and fault tests passed. | Actual provider invoices/cost reconciliation is unverified; estimated token accounting is not a bill. |
| Send scope and side effects | Receipt-to-payload invariants, explicit confirmation, actor/argument binding, replay and ambiguous-outcome tests passed. | Real external tool side effects are not claimed from fixture results. |
| Recovery / backup / restore | Recovery and migration tests passed; the two backup defects below were reproduced and repaired with focused tests. | Windows Docker Desktop installation/update/rollback on a user's machine remains `BLOCKED_EXTERNAL` for this run. Package fixtures are not runtime acceptance. |
| Windows | Local source prerequisites passed; existing CI covers bootstrap and distribution contracts. | Signing is `BLOCKED_EXTERNAL`; no signed package or fresh human install is claimed. |
| Mobile / PWA | Existing platform gate covers the production shell; Chromium/mobile emulation covers bounded daily surfaces. | Physical phone, secure deployment and screen-reader acceptance remain `BLOCKED_EXTERNAL` for this run. |
| Privacy / credentials | Redaction, scoped storage, auth, cloud fail-closed, core export/erase and provider boundaries are regression-tested. | No independent security assessment is claimed. |
| First run / contribution | No-key startup works locally and public tester/contribution paths exist. | Fresh external install/workflow evidence is still missing. |

The dogfooding protocol and deterministic soak exist. This audit does not supply seven-to-fourteen
elapsed days of human use or promote synthetic state growth into long-run acceptance.

## Findings and minimum repairs

**P0:** none reproduced in this audit's bounded scope.

| Priority | Problem / root cause | Minimum action and daily value | Existing solution / complexity / verification |
| --- | --- | --- | --- |
| P1 | Two backups created in one second use the same path; ZIP write mode truncates the earlier snapshot. | Give each new archive a unique suffix and use exclusive creation. Earlier recovery points survive repeated backups and failed later attempts. | Existing backup helper is reused; no schema, archive-format or restore redesign. Fixed-clock and forced-collision tests verify that old bytes survive and both snapshots restore. |
| P1 | The dev toolchain resolves Undici 7.29.0, affected by current advisories including [WebSocket denial of service](https://github.com/advisories/GHSA-rfgv-xxqx-mfg5) and [BalancedPool TLS validation bypass](https://github.com/advisories/GHSA-w293-vg96-wgc3). | Review a separate targeted 7.29.1 patch, then audit and verify both existing builds. This addresses developer tooling risk without a framework/provider upgrade. | Neither CodeQL nor a green PR-diff Dependency Review removes existing advisories. Production audit is clean; this is not evidence of production exploitation. |
| P2 | An empty data directory produces a successful ZIP with no `data/` entry, which restore rejects. | Stage and archive the empty directory. A backup made before first use can be restored. | Reuse v1 ZIP and existing restore. Test empty restore and preservation of the previous target directory. |
| P2 | The five-minute guide still requires API writes for Task/Decision/Outcome state despite the existing Projects → Control editor. | Prefer the existing editor in a focused first-run documentation follow-up, keeping project experiences distinct from governed Memory. | No new editor is needed; verify the exact no-key browser steps before changing instructions. |

The backup changes are locally verified. Their own PR head still requires fresh remote checks;
the starting-main and #128 results above are not checks for the changed branch.

## Independent use

**INDEPENDENT_ADOPTION_VERIFIED = 0.** Live review of issues
[#7](https://github.com/sui-ni2/personal-ai-os/issues/7),
[#15](https://github.com/sui-ni2/personal-ai-os/issues/15),
[#55](https://github.com/sui-ni2/personal-ai-os/issues/55), and
[#56](https://github.com/sui-ni2/personal-ai-os/issues/56) found no completed qualifying
external environment/version/workflow/result report. Contributor interest and intent to test
remain separate from completed use. Stars, forks, CI, bots and this maintainer-side audit do
not change that count. Use the [real-world-use path](real-world-use.md) to record successful,
partial or failed independent attempts without publishing private data.
