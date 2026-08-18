# Maintainer automation

Personal AI OS includes small, deterministic maintainer tools for repetitive review work. They are evidence helpers, not decision-makers: branch protection, required checks, maintainer review, and release policy remain authoritative.

## Safety contract

All four tools are deliberately fail-closed:

- they return `needs_review`, `blocked`, or equivalent evidence states rather than approving a pull request;
- none of them merges a pull request, changes branch protection, creates a release, or consumes provider credentials;
- missing or ambiguous evidence stays inconclusive instead of being inferred as success;
- CI/tester excerpts are bounded and redact common secret patterns before being emitted;
- external tester text is never converted automatically into verified adoption evidence.

The implementations live in `scripts/` and their focused tests live in `apps/api/tests/`.

## 1. CI failure classification

`scripts/ci_failure_classifier.py` classifies a decoded job log into a small auditable set:

- `code_or_test_failure`;
- `dependency_or_install_failure`;
- `repository_configuration_failure`;
- `external_service_failure`;
- `inconclusive`.

Specific infrastructure failures outrank generic error text. The result includes the matched rule, bounded/redacted evidence, optional workflow/job identifiers, confidence, and whether a retry is recommended. It never marks the pull request safe to merge.

```bash
python scripts/ci_failure_classifier.py job.log \
  --workflow-url https://github.com/OWNER/REPO/actions/runs/RUN_ID \
  --job-id JOB_ID
```

Tests: `apps/api/tests/test_ci_failure_classifier.py`.

## 2. Dependency update risk summary

`scripts/dependency_risk_summary.py` produces a deterministic review summary from the package, semantic-version change, runtime/development scope, affected surface, and whether the dependency is a framework/toolchain boundary.

It reports update level, risk, required checks, rationale, and review mode. `auto_merge_allowed` is always `false`; major/prerelease and other compatibility-sensitive changes remain explicit review work.

```bash
python scripts/dependency_risk_summary.py \
  --package next \
  --from-version 15.4.0 \
  --to-version 16.0.0 \
  --scope runtime \
  --surface web \
  --toolchain-or-framework \
  --release-notes-url https://example.com/release-notes
```

Tests: `apps/api/tests/test_dependency_risk_summary.py`.

## 3. Release evidence verification

`scripts/release_evidence_verifier.py` verifies a JSON evidence bundle for the exact release-candidate commit. Required evidence is:

- CI;
- CodeQL;
- Dependency Review;
- Platform Readiness;
- Release provider smoke.

A check blocks readiness when it is missing, duplicated, not successful, attached to another commit, missing an HTTPS audit URL, in the future, or older than the configured freshness window. The verifier does not create a tag or release.

```bash
python scripts/release_evidence_verifier.py evidence.json \
  --expected-sha FULL_40_CHARACTER_SHA \
  --max-age-hours 48
```

Tests: `apps/api/tests/test_release_evidence_verifier.py`.

## 4. External tester feedback triage

`scripts/tester_feedback_triage.py` classifies sanitized first-hand feedback into setup friction, documentation gap, product bug, feature request, use outcome, or inconclusive. It records whether reproduction is needed and preserves an optional HTTPS source URL.

The output always keeps `adoption_evidence` false. A maintainer must independently verify the source before any report can enter the public evidence ledger.

```bash
python scripts/tester_feedback_triage.py feedback.txt \
  --source-url https://github.com/OWNER/REPO/issues/NUMBER
```

Tests: `apps/api/tests/test_tester_feedback_triage.py`.

## Intended use with coding/API assistance

These deterministic tools establish the non-negotiable policy boundary. Coding assistants or API-backed maintainer automation can operate around them to fetch source evidence, summarize context, propose fixes, and prepare review notes, while the repository-owned scripts remain the auditable gate for classification and release evidence.

Useful future extensions include automatically collecting GitHub job metadata into the existing CI classifier, assembling release evidence bundles from required checks, and linking a genuine tester report to the fix that resolved it. Any such automation must preserve the same fail-closed rules and may not manufacture usage, approval, or adoption signals.