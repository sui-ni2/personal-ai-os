# OSS maintainer review packet

**Snapshot date:** 2026-10-22  
**Repository:** `sui-ni2/personal-ai-os`  
**License:** Apache-2.0  
**Primary maintainer:** @sui-ni2

This page is a compact index of public, reviewer-verifiable maintenance evidence. It does not replace the dated evidence ledger and it does not upgrade repository activity into end-user adoption.

## Project purpose

Personal AI OS is a local-first, provider-neutral workspace for long-running AI work. Projects, reviewed memory, tools, execution history, and continuity state belong to the workspace while model providers remain replaceable execution engines.

The current stable release is `v0.3.0`. The repository provides a documented no-key evaluation path, Windows and Docker startup paths, provider adapters, project continuity, MCP tooling, auditable execution, security gates, and maintainer automation.

## Public reach

As observed on 2026-10-22, the public repository has **59 stars and 15 forks**.

These are reach signals only. No monthly download count or independent-user count is claimed because the repository does not currently have a defensible public measure for either.

## Primary-maintainer responsibilities

The primary maintainer is responsible for:

- pull-request review and merge decisions;
- issue triage and follow-up;
- stable-release preparation and evidence verification;
- dependency and vulnerability maintenance;
- CI, CodeQL, Dependency Review, Platform Readiness, and hardening policy;
- contributor/tester intake and evidence-boundary enforcement;
- roadmap, architecture, privacy, provider, MCP, and persistence boundaries.

Repository ownership is explicit in `.github/CODEOWNERS` and `MAINTAINERS.md`.

## Concrete recent evidence

### External contribution and review

- **PR #133** — non-maintainer @yunaremaia identified and fixed incorrect project-context truncation reporting, with focused regression coverage. Contributor authorship was preserved on merge.
- The maintainer reviewed the change, requested explicit boundary coverage, waited for required checks, and thanked/credited the contributor after merge.

### Maintainer follow-through

- **PR #140** — fixed the analogous workflow-context truncation issue surfaced during review of #133 and explicitly attributed that signal instead of folding unrelated scope into the external PR.

### Security and dependency maintenance

- **PR #141** — resolved a Vite security-update blocker using the minimum patched Vite release and the compatible upstream vinext stack without weakening supply-chain controls.
- Its merge record reports CI, CodeQL, Dependency Review, Platform Readiness, and v0.4 Hardening Gates passing.

### Evidence maintenance

- **PR #142** — refreshed application-readiness, evidence-ledger, and maintainer-evidence documents to the current repository state while preserving `INDEPENDENT_ADOPTION_VERIFIED = 0`.

## Upstream open-source contribution evidence

The maintainer also contributes outside this repository. Current public FastMCP evidence includes:

- [PrefectHQ/fastmcp PR #4849](https://github.com/PrefectHQ/fastmcp/pull/4849) — merged; rejects non-positive upstream token expiry with regression coverage.
- [PrefectHQ/fastmcp PR #4861](https://github.com/PrefectHQ/fastmcp/pull/4861) — merged; adds bounded OIDC discovery caching with caller isolation and failure retry semantics.
- [PrefectHQ/fastmcp PR #4881](https://github.com/PrefectHQ/fastmcp/pull/4881) — open and mergeable at the 2026-10-22 observation; the PR records successful exact-head tests, static analysis, and downstream smoke, with maintainer review/approval still outstanding.

These links are evidence of sustained OSS contribution and review work. They are separate from Personal AI OS adoption and are not counted as user-usage evidence.

## Maintainer automation

The repository includes deterministic, tested helpers for recurring OSS maintenance work:

- CI failure classification;
- dependency-update risk summaries;
- release-evidence assembly and verification;
- external tester-feedback triage and traceability.

These tools are deliberately fail-closed. They do not merge PRs, bypass required checks, create releases, or manufacture adoption evidence. See `docs/maintainer-automation.md`.

## Security and release discipline

- `main` is protected by required pull requests and required status checks.
- CodeQL covers Python and JavaScript/TypeScript.
- Dependency Review blocks newly introduced high-severity dependency risk.
- Dependabot covers JavaScript, Python, GitHub Actions, and Docker dependency surfaces.
- Private vulnerability reporting is enabled and `SECURITY.md` directs sensitive reports away from public issues.
- Release evidence is tied to exact commits and verified before stable publication.

## Evidence boundary

**INDEPENDENT_ADOPTION_VERIFIED = 0.**

The repository currently has real public reach, active maintenance, a stable release, and a genuine external code contribution. It does **not** yet have a qualifying completed non-maintainer install/use report in Issues #7, #15, #55, or #56.

That distinction is intentional. Stars, forks, CI, maintainer dogfooding, contributor interest, and a merged external PR are not presented as proof of successful independent end-user adoption.

## Verification index

- `README.md` — runnable product and first-run paths
- `MAINTAINERS.md` — maintainer role and policy
- `SECURITY.md` — supported security line and vulnerability reporting
- `docs/maintainer-automation.md` — maintainer tooling and fail-closed contracts
- `docs/evidence-ledger.md` — dated public evidence snapshots
- `docs/maintainer-evidence-summary.md` — maintainer responsibility summary
- `docs/support-matrix.md` — automated vs maintainer vs independent verification
- `docs/application-readiness-audit.md` — dated application-facing audit
- `docs/repository-admin-checklist.md` — repository rules and security settings

This packet is intentionally concise so a reviewer can verify the underlying sources rather than rely on unsupported claims.
