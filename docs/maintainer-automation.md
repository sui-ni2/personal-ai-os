# Maintainer automation

Personal AI OS includes small, deterministic maintainer tools for repetitive review work. They are evidence helpers, not decision-makers: branch protection, required checks, maintainer review, and release policy remain authoritative.

## Safety contract

All maintainer tools are deliberately fail-closed:

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

## 5. CI evidence collector

`scripts/ci_evidence_collector.py` accepts explicit workflow/job metadata plus an optional decoded log, runs the existing deterministic classifier for non-success conclusions, and emits only bounded/redacted classification evidence. It records `needs_review` for every result, including a green job; green metadata is not merge authorization.

```bash
python scripts/ci_evidence_collector.py ci-metadata.json --log decoded-job.log
```

Tests: `apps/api/tests/test_ci_evidence_collector.py`.

## 6. Release evidence assembler

`scripts/release_evidence_assembler.py` normalizes supplied check metadata for one explicit 40-character SHA. It retains only the verifier-required fields and does not invent missing checks, successful conclusions, timestamps, URLs, or commit associations. `scripts/release_evidence_verifier.py` remains the release authority.

```bash
python scripts/release_evidence_assembler.py source-checks.json --expected-sha FULL_40_CHARACTER_SHA
```

Tests: `apps/api/tests/test_release_evidence_assembler.py`.

## 7. Dependency review assistant contract

The existing dependency summary is the deterministic input for human/Codex review. A reviewer may add release-note context and affected-surface analysis, but the final recommendation must remain one of `low-risk candidate`, `needs_review`, `blocked`, or `inconclusive`; automatic merge is prohibited. The source tool emits `needs_review` and `auto_merge_allowed=false` today, so a missing human conclusion is never promoted to low risk.

## 8. Tester-feedback traceability

`scripts/tester_feedback_traceability.py` records the real public chain `report → triage → reproduction → fix PR → external re-test` as HTTPS references. It reports missing steps and keeps both `adoption_evidence=false` and `ledger_eligible=false`, even after an external-retest URL is recorded. A maintainer must still inspect the source before updating the ledger.

```bash
python scripts/tester_feedback_traceability.py feedback-trace.json
```

Tests: `apps/api/tests/test_tester_feedback_traceability.py`.

## Intended use with coding/API assistance

These deterministic tools establish the non-negotiable policy boundary. Coding assistants or API-backed maintainer automation can operate around them to fetch source evidence, summarize context, propose fixes, and prepare review notes, while the repository-owned scripts remain the auditable gate for classification and release evidence.

Coding assistance can fetch source evidence, summarize context, propose fixes, and prepare review notes around these deterministic gates. It may not manufacture usage, approval, or adoption signals.
