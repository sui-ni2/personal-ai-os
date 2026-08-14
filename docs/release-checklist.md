# Release checklist

This checklist is the publication gate for Personal AI OS releases. A release is not considered ready because CI is green alone.

## v0.1.0 gate

### Source and repository

- [x] `main` contains the persistent project-state core.
- [x] `main` contains Standard / Advanced navigation.
- [x] Apache-2.0 license, `SECURITY.md`, and `CONTRIBUTING.md` are present.
- [x] Public README documents local startup, checks, privacy boundaries, and current runnable scope.
- [x] Package/API version is `0.1.0`.
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

- [x] Latest `main` GitHub Actions CI is green after merging the v0.1.0 feature work.
- [ ] Clean-checkout verification above has been rerun for the release candidate.

### Fresh-install real-provider smoke test

Run in an isolated temporary data/runtime location. Do not reuse or commit private user runtime databases.

- [ ] Start from a fresh clone/install with no application state.
- [ ] Application starts with no provider key and reports providers as unconfigured without exposing secret values.
- [ ] Configure one real server-side provider credential without placing the secret in Git, logs, screenshots, issues, or release artifacts.
- [ ] Run **Test connection** and receive a complete successful provider response.
- [ ] Select a provider and model, save them, and verify the choice is persisted.
- [ ] Complete one real text-chat turn and receive a complete response.
- [ ] Restart API/Web and verify the selected default provider/model and expected application state remain valid.
- [ ] Verify the user-facing failure paths for invalid credentials, unreachable/offline provider, and rate/quota limit remain distinguishable through automated tests or a safe controlled test.

### Privacy and artifact audit

- [ ] `git status` is clean before tagging.
- [ ] No `.env`, API keys, authorization headers, cookies, private conversations, runtime SQLite databases, Soccer/P5 private data, logs, uploads, or backups are included in the release diff/artifacts.
- [ ] Release notes contain no private provider responses or user data.

### Publication

Only after every required box above passes:

1. Replace `Unreleased` in `CHANGELOG.md` with the release date.
2. Merge the final release-prep change to `main` and require green CI.
3. Close Issue #1 only if its real fresh-install/provider acceptance criteria are actually satisfied.
4. Create tag `v0.1.0` from the verified `main` commit.
5. Publish GitHub Release `v0.1.0` with concise release notes and known limitations.
6. Verify the release tag points to the intended commit and no secret/private artifact is attached.

## Fail-closed rule

If the real-provider smoke test cannot be executed because no usable credential/environment is available, keep Issue #1 open and do not publish `v0.1.0`. All non-secret automated and repository checks may still be completed in advance.
