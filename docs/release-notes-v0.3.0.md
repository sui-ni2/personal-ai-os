# Personal AI OS v0.3.0 — Release Notes

> Release candidate notes. Publication requires one fresh successful result for every gate in
> `docs/release-checklist.md`; a tag or GitHub Release is not implied by this document.

Personal AI OS v0.3.0 strengthens continuity for long-running, provider-neutral work while keeping
the application local-first and credentials server-side.

## Highlights

- Project handoff snapshots provide bounded compact and full continuity views with explicit user
  actions, preview-before-copy behavior, and no duplicate client-side persistence.
- Projects now have explicit crash/restart recovery sessions that use bounded persisted metadata,
  require preview and confirmation, and exclude provider sessions, conversations, credentials,
  transition receipts, and private reasoning.
- Tenant-scoped generic Project creation supports provider-neutral research and build work without
  adding domain-specific fields to the shared project model.
- Maintainer tools classify CI failures, summarize dependency risk, assemble and verify exact-SHA
  release evidence, and preserve tester-feedback traceability with fail-closed behavior.

## Security and release integrity

- The repository ruleset requires pull requests, required checks, resolved review threads, and
  prohibits force pushes and branch deletion on `main`.
- The v0.3.0 candidate updates the Web workspace version to `0.3.0` to align it with the API and
  internal Python packages.
- The transitive `nanoid` resolution is updated to `3.3.18`, addressing Dependabot alert #3
  (`GHSA-2v37-7h3g-55p8` / `CVE-2026-67213`).
- CI, CodeQL, Dependency Review, Platform Readiness, and a real-provider smoke must all be
  recorded against one exact candidate SHA before tagging.

## Privacy and known limitations

- Remote provider credentials remain server-side and are not returned by Settings.
- Recovery and handoff paths are intentionally bounded and project-scoped; they are not a chat or
  provider-session export mechanism.
- The current distribution remains community/self-hosted. Cloud accounts, billing, managed routing,
  and device sync are not live.
- Independent adoption is not claimed. Public reach, CI activity, and maintainer work remain
  separate from external installation or workflow evidence.

## Verification and feedback

Release evidence is verified with `scripts/release_evidence_verifier.py`. Users can submit
sanitized first-run, first-chat, restart-persistence, and platform feedback through the public issue
forms. Never include API keys, `.env` contents, cookies, private conversations, runtime databases,
or secret-bearing logs in reports.
