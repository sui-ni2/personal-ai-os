# Verification support matrix

This matrix separates automated repository coverage, maintainer-side evidence, and genuinely independent user verification. It is intentionally conservative: CI success is not counted as third-party adoption.

**Observation date:** 2026-08-28

| Path | Repository / CI evidence | Maintainer-side evidence | Independent user verification | Current limitation |
|---|---|---|---|---|
| Isolated no-key startup | `scripts/release-provider-smoke.py --provider openai --no-key-only` is part of the documented readiness path and normal repository checks | The project documents the expected PASS contract: startup, `v0.2.0` health, unconfigured-provider behavior, and secret redaction | None verified yet | Does not prove a real provider connection or model response |
| Windows source bootstrap | Platform Readiness exercises `scripts/setup-windows.ps1` on `windows-latest` | Guarded bootstrap and `-CheckOnly` behavior are documented in README and `docs/try-without-api.md` | None verified yet; Issue #15 requests a fresh external Windows test | CI cannot reproduce every local Windows configuration |
| Docker Compose local start | Platform Readiness builds, starts, health-checks, and exercises the localhost-only Compose path | The repository documents `docker compose up --build -d` as the lowest-friction no-key path | None verified yet; Issue #56 has external tester interest but no completed environment/result report | CI coverage and intent to test are not equivalent to independent macOS/Linux/Windows use |
| Provider-backed first chat and restart persistence | Release/provider smoke infrastructure exists for release candidates | Issue #7 defines the real provider → first chat → restart-persistence validation path | None verified yet | Requires a tester-owned supported provider credential or explicitly enabled local provider |
| Ongoing real-world workflow | The product and issue templates provide a reproducible place to report partial or failed use | Issue #55 defines the real-world-use evidence boundary | None verified yet; contributor interest without actual use is not counted | A contribution request or star/fork does not establish workflow adoption |
| Mobile/PWA readiness | Platform Readiness includes mobile/PWA checks | Deployment and secure-context constraints are documented | None verified yet | Automated readiness does not replace physical-device verification |

## Evidence rules

- A green CI run proves only the checks represented by that workflow.
- Maintainer dogfooding is first-party product evidence, not independent adoption.
- Stars and forks are reach signals, not proof that the software was installed or used successfully.
- A statement that someone plans to test is not a verification result.
- An independent verification entry requires a public issue, pull request, or comment that identifies the tested path, environment, version/commit, and result without exposing private data.
- Negative or failed tests remain valid evidence and should not be removed merely because they are unfavorable.

## How to close the gaps

- Windows fresh install: use Issue #15.
- macOS/Linux Docker path: use Issue #56.
- First run / provider / persistence: use Issue #7.
- Ongoing real-world workflow: use Issue #55 or the `Real-world use` issue form.

See `docs/evidence-ledger.md` for the dated project evidence snapshot and `docs/real-world-use.md` for the evidence boundary.