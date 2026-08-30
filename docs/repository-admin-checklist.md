# Repository admin checklist

These settings live in GitHub repository administration rather than the source tree. They are tracked separately because source-level CI cannot enforce or replace them.

## Discoverability

- [x] Focused repository topics are configured and verified.

Current set:

- `personal-ai`
- `ai-workbench`
- `mcp`
- `openai`
- `anthropic`
- `ollama`
- `self-hosted`
- `privacy`
- `developer-tools`

Avoid broad or misleading tags that imply integrations or production capabilities the repository does not have.

## Main branch protection

- [x] The default branch is protected by the active repository ruleset `Protect main`.

Verified policy:

- pull requests are required before merge;
- required GitHub Actions checks are `backend`, `frontend`, `Analyze (javascript-typescript)`, `Analyze (python)`, and `dependency-review`;
- review conversations must be resolved before merge;
- force pushes are blocked;
- branch deletion is blocked;
- there is no routine bypass actor;
- external approval is not required while the project has only one trusted maintainer.

If a second trusted maintainer is added, reassess whether an approval requirement improves review quality without making maintenance brittle.

## Security analysis settings

- [x] Dependency graph is enabled. The previously failing Dependency Review run was rerun after the repository setting changed and completed successfully.
- [x] Pull-request Dependency Review is present and fails on newly introduced high-severity dependency risk according to the source-controlled workflow policy.
- [x] CodeQL is configured for Python and JavaScript/TypeScript.
- [x] Dependabot version updates are configured; production Docker runtime **major** jumps remain deliberate compatibility work rather than automatic version-update PRs.
- [x] GitHub private vulnerability reporting is enabled.
- [x] `SECURITY.md` directs vulnerability reports to GitHub's private reporting flow and keeps sensitive exploit details, credentials, private conversations, logs, and deployment data out of public issues.

## Discussions

Enable GitHub Discussions when there is enough external traffic to justify a lower-friction Q&A/ideas channel. Keep reproducible bugs and release blockers in Issues so they remain actionable.

## Release evidence

- [x] `v0.2.0` is a stable tag on the verified release commit.
- [x] The release candidate passed CI, CodeQL, Dependency Review, Platform Readiness, and the application-level real-inference release smoke before tagging.
- [x] Live GitHub verification on 2026-08-30 found `v0.2.0` as a tag and **zero GitHub Releases**. Do not claim a public v0.2.0 Release, release notes, or assets until the formal publication action succeeds and is re-verified.
- [x] `.github/workflows/publish-release.yml` provides a fail-closed publication path. Manual runs require an existing valid tag reachable from `main`; automatic runs only consider an existing strict stable `vN.N.N` tag and no-op if the GitHub Release already exists.

Future stable releases must keep the same evidence standard: real application-level inference, restart/persistence verification, normal CI/security/platform checks, an explicit stable tag, and an auditable release publication path. A successful model download or mock alone does not satisfy the release gate.

## Adoption evidence boundary

Repository hardening, CI, release management, Stars, and Forks are useful maintenance/discoverability signals but are not proof that someone has successfully used the software. Genuine tester comments, reproducible external issues, focused external pull requests, and independently verifiable user stories remain the preferred adoption evidence.
