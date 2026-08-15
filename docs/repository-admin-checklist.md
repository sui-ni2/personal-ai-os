# Repository admin checklist

These settings live in GitHub repository administration rather than the source tree. They are tracked separately because source-level CI cannot enforce or replace them.

## Discoverability

Add focused repository topics after confirming they accurately describe the project. Recommended starting set:

- `personal-ai`
- `ai-workbench`
- `mcp`
- `openai`
- `anthropic`
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

This is a real gap today: an administrator can currently write directly to `main`, so the project process is stronger than the repository enforcement.

## Security analysis settings

Enable the repository **Dependency graph** before adding the Dependency Review workflow. A real trial of `actions/dependency-review-action@v5` failed closed because GitHub reported that Dependency Review is not supported while the graph is disabled. Once the graph is enabled, add the pull-request Dependency Review gate back and fail on newly introduced `high` or `critical` vulnerabilities.

GitHub private vulnerability reporting is also currently disabled. Enable it when possible, then update `SECURITY.md` to point reporters directly to the private reporting flow instead of asking them to establish a private channel first.

CodeQL is already configured in source control for Python and JavaScript/TypeScript. Dependabot version updates are also configured; production Docker runtime **major** jumps remain deliberate compatibility work rather than automatic version-update PRs.

## Discussions

Enable GitHub Discussions when there is enough external traffic to justify a lower-friction Q&A/ideas channel. Keep reproducible bugs and release blockers in Issues so they remain actionable.

## Release gate

Do not weaken the real-provider release gate merely because repository-level settings are incomplete. `v0.2.0` remains blocked until the required real-provider smoke test passes with a real credential.
