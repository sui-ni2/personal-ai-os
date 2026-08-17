# Security Policy

## Supported versions

Security fixes target the latest stable `v0.2.x` release line and the current `main` branch.
Versions older than `v0.2.0` are pre-stable historical builds and are not supported.
When a fix affects the current stable release, maintainers will decide whether a focused
backport is safer than requiring users to move to the next stable release.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting flow for this repository to report
potential security vulnerabilities. Do not open a public issue or discussion for a report
that contains exploit details, credentials, private user data, deployment secrets, private
conversations, sensitive logs, or other confidential information.

Include the affected version or commit, impact, reproduction conditions, and a minimal
proof of concept only in the private report, with all unrelated secrets and personal data
removed. Please allow reasonable time for confirmation and remediation before public
disclosure.

If GitHub's private reporting flow is temporarily unavailable, contact the maintainer
through the public GitHub profile without including sensitive details and request a private
channel. Do not paste sensitive material into a public issue, discussion, or profile message.

## Security boundaries

- Provider credentials remain server-side and must never reach the browser.
- MCP tools and fixed-command connectors are allowlisted and permission-checked.
- Public functional deployments require access protection; anonymous API exposure is
  unsupported.
- Runtime databases, conversations, logs, uploads, backups, and private project
  artifacts are outside the open-source distribution.
