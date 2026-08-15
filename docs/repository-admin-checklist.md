# Repository admin checklist

These settings live in GitHub repository administration rather than the source tree. They are tracked separately because source-level CI cannot enforce or replace them.

## Discoverability

Add focused repository topics after confirming they accurately describe the project. Recommended starting set:

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

Protect `main` (or use a repository ruleset) so that normal changes go through pull requests and required CI.

Target policy:

- require a pull request before merge;
- require the existing backend and frontend CI checks to pass;
- block force pushes and branch deletion;
- keep maintainer bypass exceptional rather than routine;
- do not require an external approval while the project has only one maintainer, unless a second trusted maintainer is added.

The connected GitHub integration cannot read the branch-protection endpoint for this repository, so this setting remains an explicit repository-admin verification item rather than source-controlled evidence.

## Security analysis settings

- [x] Dependency graph is enabled. The previously failing Dependency Review run was rerun after the repository setting changed and completed successfully.
- [x] Pull-request Dependency Review is present and fails on newly introduced high-severity dependency risk according to the source-controlled workflow policy.
- [x] CodeQL is configured for Python and JavaScript/TypeScript.
- [x] Dependabot version updates are configured; production Docker runtime **major** jumps remain deliberate compatibility work rather than automatic version-update PRs.
- [ ] GitHub private vulnerability reporting is currently disabled. Enable it when possible, then update `SECURITY.md` to point reporters directly to the private reporting flow instead of asking them to establish a private channel first.

## Discussions

Enable GitHub Discussions when there is enough external traffic to justify a lower-friction Q&A/ideas channel. Keep reproducible bugs and release blockers in Issues so they remain actionable.

## Release gate

Do not weaken the real-provider release gate merely because repository-level settings are incomplete. `v0.2.0` remains blocked until the required real-inference smoke test completes successfully. The fallback local Ollama path is valid only when the workflow installs a real runtime, loads a real model, and completes the application-level connection/chat/restart loop; mocks or a successful model download alone do not satisfy the gate.
