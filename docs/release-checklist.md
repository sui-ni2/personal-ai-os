# Release checklist

This checklist is the publication gate for Personal AI OS releases. A release is not considered ready because CI is green alone.

## v0.2.0 gate

### Version history

- [x] Historical tag `v0.2.0-alpha.1` exists and is an ancestor of the v0.2 release line.
- [x] No GitHub Release was published for `v0.2.0-alpha.1`; the tag remains intact as historical prerelease evidence.
- [x] The next stable release line is `v0.2.0`, not a chronological rollback to `v0.1.0`.

### Source and repository

- [x] The release candidate contains the persistent project-state core.
- [x] The release candidate contains Standard / Advanced navigation.
- [x] Apache-2.0 license, `SECURITY.md`, and `CONTRIBUTING.md` are present.
- [x] Public README documents local startup, checks, privacy boundaries, and current runnable scope.
- [x] API, internal Python packages, and Web package are aligned to version `0.2.0`.
- [x] `CHANGELOG.md` is dated `2026-08-15` before tagging.

### Automated verification

The final release candidate is verified through the equivalent automated clean-checkout paths below:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall -q apps/api/src packages
pnpm check:web
pnpm build:web
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-mobile-readiness.ps1 -BaseUrl "http://127.0.0.1:3001" -AllowInsecureLocalhost
```

- [x] Backend tests pass, including provider failure guidance and Ollama output-cap coverage.
- [x] Python package/API version consistency and compilation pass.
- [x] Frontend type checks and production build pass.
- [x] Windows fresh no-key readiness passes.
- [x] Production Docker image builds, starts, and passes health checks.
- [x] Production PWA/mobile readiness passes against the running production image.
- [x] Dependency Review passes with the source-controlled high-severity gate restored.
- [x] CodeQL passes for the release candidate.
- [x] Platform Readiness passes for the release candidate.

### Fresh-install real-provider smoke test

A valid release gate must execute a **real model inference request**, not a mock, fixture, synthetic response, or disabled provider. The release workflow prefers a maintainer-configured OpenAI or Anthropic server-side secret when one exists. Otherwise it installs a pinned Ollama runtime on the isolated GitHub Actions runner, pulls the allowlisted small CI model, and exercises the same application provider boundary through Ollama's local OpenAI-compatible endpoint.

Ollama is disabled during the fresh no-provider phase and enabled only for the real-inference phases. Its local endpoint requires no provider credential. CI applies an explicit small output-token cap only to the release runner so model verbosity cannot make the gate nondeterministic; normal Ollama usage remains uncapped unless the operator explicitly configures a limit.

- [x] Start from an isolated fresh runtime with no application state.
- [x] Application starts with no provider enabled/credential configured and reports providers as unconfigured without exposing secret values.
- [x] Explicitly enable one real provider without placing a secret in Git, logs, screenshots, issues, or release artifacts.
- [x] Run the provider connection check and receive a complete successful model response.
- [x] Select a provider and model, save them, and verify the choice is persisted.
- [x] Complete one real text-chat turn and receive a complete non-empty response.
- [x] Restart the API against the same isolated data directory and verify the selected default provider/model and persisted conversation remain valid.
- [x] Continue the same conversation after restart and verify the application persists the additional exchange.
- [x] Verify invalid-credential, unreachable/offline, and rate/quota-limit failure categories through automated API/provider tests.

### Privacy and artifact audit

- [x] Final PR file list contains only source, tests, workflows, public documentation, and `.env.example`; no unexpected generated/runtime file is present.
- [x] No `.env` values, API keys, authorization headers, cookies, private conversations, runtime SQLite databases, Soccer/P5 private data, logs, uploads, model cache files, or backups are included in the release diff.
- [x] Release notes contain no private provider response text or user data.
- [x] The release smoke runner does not print model response text or provider credentials.

### Verified evidence

PR #35 release head `a2e09202448e543eb99c20a7085e2e3b9408a4ef` passed all five release lines before the checklist-only evidence update:

- CI — success
- CodeQL — success
- Dependency Review — success
- Platform Readiness — success, including Windows no-key and production Docker/PWA checks
- Release provider smoke — success with real local Ollama inference, persisted provider/model selection, API restart, and continued conversation state

The checklist-only update also remained green before merge.

### Publication — tag fact

- [x] PR #35 merged to `main`.
- [x] Historical release-gate evidence is recorded above for the tag decision.
- [x] Issue #1 was closed as completed with sanitized acceptance evidence.
- [x] Stable tag `v0.2.0` points to the intended verified `main` commit.
- [x] Live GitHub evidence check on 2026-08-30 found the `v0.2.0` tag but **zero GitHub Releases**. This is a tagged release line only; no GitHub Release, notes, or assets are claimed.

## v0.3.0 release

**Verified release candidate:** `8e14e857ffbae642268ea069c9b9d1f0c72f5cdd`.

- [x] CI — success: [run 33351296808](https://github.com/sui-ni2/personal-ai-os/actions/runs/33351296808).
- [x] CodeQL — success: [run 33351296814](https://github.com/sui-ni2/personal-ai-os/actions/runs/33351296814).
- [x] Dependency Review — success: [run 33351296818](https://github.com/sui-ni2/personal-ai-os/actions/runs/33351296818).
- [x] Platform Readiness — success: [run 33351296833](https://github.com/sui-ni2/personal-ai-os/actions/runs/33351296833).
- [x] Release provider smoke — success: [run 33351296811](https://github.com/sui-ni2/personal-ai-os/actions/runs/33351296811). This is the release-branch real-provider gate, not an ordinary PR skip.
- [x] `scripts/release_evidence_verifier.py` returned `ready_to_tag` with no blockers using GitHub's server time.
- [x] Release PR [#90](https://github.com/sui-ni2/personal-ai-os/pull/90) merged to `main` as `e5275ef24d5154974c324121db41bb870bac049c`.
- [x] Annotated tag `v0.3.0` resolves to the verified candidate SHA above and is reachable from `main`.
- [x] [GitHub Release v0.3.0](https://github.com/sui-ni2/personal-ai-os/releases/tag/v0.3.0) was published on 2026-08-31.

The verifier allowed normal release review; it did not replace the repository ruleset, release-PR merge, tag validation, or publication workflow.

## Fail-closed rule

If a future release's real-provider smoke test cannot execute or does not complete successfully, do not create its stable release tag or publish its GitHub Release. The existence of a workflow, a successful model download, or green unit tests is not release evidence by itself; the complete application-level real-inference loop must pass.
