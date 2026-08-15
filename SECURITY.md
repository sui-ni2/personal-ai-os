# Security Policy

## Supported versions

Security fixes currently target the latest code on the default branch. A formal
multi-version support policy will be published with the first stable release.

## Reporting a vulnerability

Do not report vulnerabilities that contain credentials, private user data, exploit
details, or sensitive deployment information in a public issue.

GitHub private vulnerability reporting is not currently enabled for this repository.
Until it is enabled, contact the maintainer through the public GitHub profile without
including sensitive details and request a private channel. Do not paste a proof of
concept, credential, private conversation, deployment secret, or sensitive log into a
public issue or discussion.

Include the affected version or commit, impact, reproduction conditions, and a minimal
proof of concept only after a private reporting channel is established, with all secrets
and personal data removed. Please allow reasonable time for confirmation and remediation
before public disclosure.

## Security boundaries

- Provider credentials remain server-side and must never reach the browser.
- MCP tools and fixed-command connectors are allowlisted and permission-checked.
- Public functional deployments require access protection; anonymous API exposure is
  unsupported.
- Runtime databases, conversations, logs, uploads, backups, and private project
  artifacts are outside the open-source distribution.
