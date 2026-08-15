# Release checklist

This checklist is the publication gate for Personal AI OS releases. A release is not considered ready because CI is green alone.

## v0.2.0 gate

### Version history

- [x] Historical tag `v0.2.0-alpha.1` exists and is an ancestor of current `main`.
- [x] No GitHub Release was published for `v0.2.0-alpha.1`; the tag remains intact as historical prerelease evidence.
- [x] The next stable release line is `v0.2.0`, not a chronological rollback to `v0.1.0`.

### Source and repository

- [x] `main` contains the persistent project-state core.
- [x] `main` contains Standard / Advanced navigation.
- [x] Apache-2.0 license, `SECURITY.md`, and `CONTRIBUTING.md` are present.
- [x] Public README documents local startup, checks, privacy boundaries, and current runnable scope.
- [x] API, internal Python packages, and Web package are aligned to version `0.2.0` in the release candidate.
- [ ] `CHANGELOG.md` is switched from `Unreleased` to the actual release date immediately before tagging.

### Automated verification

Before publishing, all of the following must pass from a clean checkout:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall -q apps/api/src packages
pnpm check:web
pnpm build:web
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-mobile-readiness.ps1 -BaseUrl "http://127.0.0.1:3001" -AllowInsecureLocalhost
```

- [x] Latest `main` GitHub Actions CI is green after merging the core v0.2 feature work and release-gate documentation.
- [ ] Clean-checkout verification above has been rerun for the final release candidate after version alignment.
- [ ] Release-branch CI, CodeQL/Dependency Review as applicable, and Platform Readiness are green for the final diff.

### Fresh-install real-provider smoke test

Run in an isolated temporary data/runtime location. Do not reuse or commit private user runtime databases.

A valid release gate must execute a **real model inference request**, not a mock, fixture, synthetic response, or disabled provider. The release workflow prefers a maintainer-configured OpenAI or Anthropic server-side secret when one exists. Otherwise it installs a pinned Ollama runtime on the isolated GitHub Actions runner, pulls the allowlisted small CI model, and exercises the same application provider boundary through Ollama's local OpenAI-compatible endpoint.

Ollama is disabled during the fresh no-provider phase and enabled only for the real-inference phases. Its local endpoint requires no provider credential; this does not weaken the gate because an actual model is loaded and queried.

- [ ] Start from a fresh clone/install with no application state.
- [ ] Application starts with no provider enabled/credential configured and reports providers as unconfigured without exposing secret values.
- [ ] Configure or explicitly enable one real provider without placing a secret in Git, logs, screenshots, issues, or release artifacts.
- [ ] Run the provider connection check and receive a complete successful model response.
- [ ] Select a provider and model, save them, and verify the choice is persisted.
- [ ] Complete one real text-chat turn and receive a complete non-empty response.
- [ ] Restart the API against the same isolated data directory and verify the selected default provider/model and persisted conversation remain valid.
- [ ] Continue the same conversation after restart and verify the application persists the additional exchange.
- [ ] Verify user-facing invalid-credential, unreachable/offline, and rate/quota-limit failure categories remain distinguishable through automated tests or a safe controlled test.

### Privacy and artifact audit

- [ ] Final release-prep diff has no unexpected generated/runtime files before tagging.
- [ ] No `.env`, API keys, authorization headers, cookies, private conversations, runtime SQLite databases, Soccer/P5 private data, logs, uploads, model cache files, or backups are included in the release diff/artifacts.
- [ ] Release notes contain no private provider responses or user data.

### Publication

Only after every required box above passes:

1. Replace `Unreleased` in `CHANGELOG.md` with the release date.
2. Merge the final release-prep change to `main` and require green CI.
3. Close Issue #1 only if its real fresh-install/provider acceptance criteria are actually satisfied.
4. Create tag `v0.2.0` from the verified `main` commit.
5. Publish GitHub Release `v0.2.0` with concise release notes and known limitations.
6. Verify the release tag points to the intended commit and no secret/private artifact is attached.

## Fail-closed rule

If the real-provider smoke test cannot execute or does not complete successfully, keep Issue #1 open and do not publish `v0.2.0`. The existence of a workflow, a successful model download, or green unit tests is not release evidence by itself; the complete application-level real-inference loop must pass.
