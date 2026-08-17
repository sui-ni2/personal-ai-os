# Repository admin checklist

These settings live in GitHub repository administration rather than the source tree. They are tracked separately because source-level CI cannot enforce or replace them.

## Discoverability

- [ ] Add focused repository topics. The repository API currently reports no topics.

Recommended starting set:

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

- [ ] Protect `main` (or use a repository ruleset) so that normal changes go through pull requests and required CI. The repository API currently reports `main` as unprotected.

Target policy:

- require a pull request before merge;
- require the existing backend/frontend CI and security checks to pass;
- block force pushes and branch deletion;
- keep maintainer bypass exceptional rather than routine;
- do not require an external approval while the project has only one maintainer, unless a second trusted maintainer is added.

The connected GitHub integration does not expose a branch-protection write action, so this remains a repository-admin task rather than source-controlled evidence.

## Security analysis settings

- [x] Dependency graph is enabled. The previously failing Dependency Review run was rerun after the repository setting changed and completed successfully.
- [x] Pull-request Dependency Review is present and fails on newly introduced high-severity dependency risk according to the source-controlled workflow policy.
- [x] CodeQL is configured for Python and JavaScript/TypeScript.
- [x] Dependabot version updates are configured; production Docker runtime **major** jumps remain deliberate compatibility work rather than automatic version-update PRs.
- [ ] GitHub private vulnerability reporting is currently disabled. Enable it when possible, then update `SECURITY.md` to point reporters directly to the private reporting flow instead of asking them to establish a private channel first.

## Discussions

Enable GitHub Discussions when there is enough external traffic to justify a lower-friction Q&A/ideas channel. Keep reproducible bugs and release blockers in Issues so they remain actionable.

## Release evidence

- [x] `v0.2.0` is a stable tag on the verified release commit.
- [x] The release candidate passed CI, CodeQL, Dependency Review, Platform Readiness, and the application-level real-inference release smoke before tagging.
- [x] `Personal AI OS v0.2.0` is published as a public GitHub Release; it is neither a draft nor a prerelease.
- [x] `.github/workflows/publish-release.yml` provides a fail-closed publication path. Manual runs require an existing valid tag reachable from `main`; automatic runs only consider an existing strict stable `vN.N.N` tag and no-op if the GitHub Release already exists.

Future stable releases must keep the same evidence standard: real application-level inference, restart/persistence verification, normal CI/security/platform checks, an explicit stable tag, and an auditable release publication path. A successful model download or mock alone does not satisfy the release gate.
