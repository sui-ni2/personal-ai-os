# Application readiness audit

**Observed:** 2026-08-30. **Authority order:** live GitHub repository facts, then this local worktree. This audit does not treat a local commit, generated file, or workflow definition as proof that a remote check or GitHub Release exists.

| Item | Status | Fresh finding |
| --- | --- | --- |
| `main` | VERIFIED | Protected remote `main` is `3f974bf514c874f3f3d26efd8f1d64388ce0d837`. |
| `release/v0.3.0` | VERIFIED | Remote candidate is `493717f091c8e0c427e473c35c1db01dc7392d2f`, eight commits ahead of `main`. |
| `v0.2.0` tag | VERIFIED | Lightweight tag points to `934efa959d2487c6942951d90bb543b4104369f6`. |
| `v0.2.0` GitHub Release / notes / assets | MISSING | Live GitHub Releases query returned zero releases. No public Release, Release notes, or Release assets may be claimed. |
| README / release docs before this audit | CONTRADICTED | Several public documents said a `v0.2.0` GitHub Release remained available, contrary to the live Release query. |
| `CHANGELOG.md` | PARTIAL | Contains a useful tagged-release entry, but its old sentence claiming a published GitHub Release required correction. |
| `SECURITY.md`, `CONTRIBUTING.md`, `AGENTS.md` | VERIFIED | Present and aligned with local-first, no-secret, project-contract boundaries. |
| Evidence ledger and maintainer summary before this audit | CONTRADICTED | Both repeated the nonexistent v0.2.0 GitHub Release claim and listed four rather than five open issues. |
| Issue #7 / #15 / #55 / #56 | VERIFIED | Open external-validation entry points. No completed independent result was found. |
| Issue #85 | PARTIAL | Open; bounded handoff UI existed, but crash/restart recovery did not. This worktree adds the missing recovery path pending CI/review. |
| Open pull requests | VERIFIED | Zero at observation time. |
| Reach | VERIFIED | 59 stars, 14 forks, 2 subscribers/watchers at observation time. These are not adoption evidence. |
| External contributor / tester evidence | MISSING | No qualifying non-maintainer install result, real workflow result, focused external PR, or external re-test was identified. |
| Independent adoption | MISSING | `INDEPENDENT_ADOPTION_VERIFIED = 0`. |
| CI on v0.3.0 base SHA | PARTIAL | CI backend and frontend jobs succeeded in run `33155548426` for `493717f…`. |
| CodeQL on v0.3.0 base SHA | MISSING | No check run attached to the exact v0.3.0 SHA. |
| Dependency Review on v0.3.0 base SHA | MISSING | No check run attached to the exact v0.3.0 SHA. |
| Platform Readiness on v0.3.0 base SHA | MISSING | No check run attached to the exact v0.3.0 SHA. |
| Release provider smoke on v0.3.0 base SHA | MISSING | No successful exact-SHA run was found. |
| Release evidence verifier | BLOCKED_EXTERNAL | The exact-SHA bundle lacks four required fresh remote gates, so the verifier must remain blocked. |
| Docker / Windows / mobile / privacy | PARTIAL | Source-controlled checks and documented paths exist; the v0.3.0 candidate still needs exact-SHA Platform Readiness evidence. |
| Current worktree checks | PARTIAL | Full local API tests (with two existing skips), Python compilation, version consistency, and no-key provider smoke passed. Frontend dependencies could not complete installation because registry tarball requests timed out; this remains local evidence only. |

## Consequence

The release decision is **RELEASE_BLOCKED**. A tag or GitHub Release must not be created or implied until a frozen new release-candidate SHA has one fresh successful result for every verifier-required gate: CI, CodeQL, Dependency Review, Platform Readiness, and Release provider smoke.

The application evidence is useful for maintainer activity and product direction, but independent adoption remains an external-evidence gap that code cannot manufacture.
