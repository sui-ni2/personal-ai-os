# Project State Reconciler — read-only v1 design

**Status:** PAI-004 read-only metadata API v1 merged in PR #170 as `fb9008167b013e3d19dbfc50323cbf1b4e5412e2`; PR #172 reconciled its delivery register. PAI-034 Projects evidence review and structural metadata classification merged in PR #174 as `8ad1d7f77488f7be33f64190dc2d2cb4b005d831`. Final exact-head PR checks and post-merge main CI, CodeQL and Platform Readiness passed; provider smoke was skipped. No semantic cross-source reconciliation or external user pilot is claimed.
**Parent workstreams:** PAI-004 read-only API v1 and PAI-034 Projects preview/classification in [project delivery register](project-delivery-register.md).
**Existing implementation to reuse:** [persistent project state](persistent-project-state.md), [bounded handoff](project-handoff.md), [recovery](project-handoff.md#restart-recovery), and the Project Control Center.

## Problem

The application persists tasks, decisions, outcomes, workflow positions, reviewed memory,
and recovery evidence. However, a persisted record, a workflow marked completed, a model
statement, and a confirmed external action are **different kinds of evidence**. Collapsing
them into one checkmark can mislead a user resuming a long-running project.

Merged PR #169 removes unconditional UI completion checkmarks and adds a bounded list of next
recorded workflow steps. This RFC addresses the **next** increment; it must not duplicate
or overwrite that PR.

## v1 objective and non-goals

Provide an explicit, tenant/project-scoped, **read-only reconciliation preview** so users
can answer: what is persistently recorded, what is the next recorded step, and what still
needs confirmation? No automatic promotion of tasks, workflow steps, outcomes, or external
side effects to complete is allowed.

**Excluded:** automatic conflict resolution, provider or agent session import, arbitrary
external account actions, upload/download of private source data, full audit export,
cross-project matching, cloud tenant resolution, database migrations, unbounded retrieval,
and automatic release or publication decisions.

## Implemented v1 API contract (metadata only)

PR #170 implements the opt-in endpoint:

`GET /api/projects/{project_id}/control-center/reconciliation-preview?limit=20`

The route checks that the project exists and reuses the existing project/tenant-scoped
state and workflow stores. `limit` is constrained to 1–100. Each store returns an
original total count plus at most `limit` rows using SQL-level bounded reads.

The current response contains:

- `project_id`, `read_at`, and `evidence_scope=PERSISTED_RECORDS_ONLY`;
- `counts.states` and `counts.workflows`, plus an explicit `truncated` flag;
- `state_records`: namespace, key, version and storage status, labelled
  `RECORDED` / `STORED_NOT_EXECUTION_PROOF`;
- `workflow_records`: workflow ID, run key, version, recorded status and next step,
  labelled `WORKFLOW_POSITION` with `external_execution=UNVERIFIED`.

The state query does not select or deserialize private `value_json`. The workflow
query does not read transition evidence. The endpoint is read-only and does not create
a second state store.

This v1 does **not** yet return a state fingerprint, classify `CONFLICT` or
`INSUFFICIENT_EVIDENCE`, or render a user-facing Projects preview. Those remain
future increments rather than capabilities to infer from the current response.

The response must never contain provider credentials, raw conversations, chain-of-thought,
tool payload bodies, unreviewed memory values, prior transition evidence, authorization
headers, or another project's storage records. Only actor-authorized metadata is eligible.

## Evidence classification (invariants)

The original PAI-004 API v1 emitted only `RECORDED` and `WORKFLOW_POSITION`. PAI-034 extends the same bounded endpoint with deterministic metadata-only classifications; it does not add a writable reconciliation action.

| Label | Meaning | Never infer |
| --- | --- | --- |
| `RECORDED` | A versioned state row or returned execution result is stored | Action executed or user independently verified |
| `WORKFLOW_POSITION` | Workflow cursor, status and next recorded step are stored consistently | External side effect happened |
| `NEEDS_CONFIRMATION` | An external side effect is still started/unknown, or retry requires explicit confirmation | Success from assistant prose, CI, or tool intent |
| `CONFLICT` | Current state/history versions or workflow cursor/transition versions contradict each other | Overwrite the newest or locked state |
| `INSUFFICIENT_EVIDENCE` | Expected state/transition history is missing, a status is unrecognized, or the bounded preview is truncated | Invent missing evidence |

A workflow with `status=completed` **only** means its own recorded steps reached the
terminal position. A separate verified external effect needs a specific receipt in the
authoritative execution/confirmation system. Public CI green is not product adoption.

### PAI-034 deterministic metadata rules

- State history expects versions `1..current_version-1`. A missing row is
  `INSUFFICIENT_EVIDENCE`; duplicate, future or contradictory versions are
  `CONFLICT`. A locked state remains `RECORDED` with `review_required=true`:
  a lock is protection, not proof of conflicting values.
- Workflow version must match its cursor, terminal status and transition versions.
  Missing transitions are `INSUFFICIENT_EVIDENCE`; inconsistent cursors or
  transition versions are `CONFLICT`. External execution remains `UNVERIFIED`.
- Only tenant/project-scoped execution rows involving an external side effect or
  explicit retry confirmation are included. `started`/`outcome_unknown` and
  `retry_requires_confirmation` are `NEEDS_CONFIRMATION`. A completed tool
  response is merely `RECORDED`, not independent proof of the external result.
- The endpoint selects no state values, transition evidence, execution detail JSON,
  provider/model identifiers, credentials or conversation content. A fingerprint is
  computed from returned metadata only. Truncation is explicit and raises the
  overall review flag.
- Optimistic-concurrency rejections return HTTP 409 to the caller but are not stored
  as durable conflict receipts. The preview therefore reports only contradictions
  visible in persisted metadata; it does not invent a historical conflict from a
  rejected write attempt.
- The Projects panel loads only on user request. Closing it aborts any pending read
  and discards the in-memory snapshot; it performs no writes.


## Safety and concurrency

1. Identity, tenant and project access are checked before touching any project store.
2. Snapshot and project state come from the same existing authority, never reconstructed
   from chat text or transferred provider sessions.
3. Preview is read-only and bounded; `truncated` remains explicit even if the first page
   looks healthy.
4. A stale expected version produces `CONFLICT`/review, not silent overwrite.
5. Ambiguous external execution returns `NEEDS_CONFIRMATION`, not an automatic retry.
6. No model-generated status may become authoritative without an explicit human action.
7. Background logs and generic Activity events show only bounded metadata, never private
   values or cross-project IDs that would expose another user's content.
8. Closing the preview discards client-side snapshot state; no second persisted copy.

## Build sequence and acceptance gates

1. **Read-only API v1 — completed in PR #170:** metadata-only state/workflow records,
   SQL-bounded reads, project scoping, explicit truncation and no external-completion claim.
2. **PAI-034 classification and Projects preview — completed in PR #174:** deterministic
   state-history, workflow-transition and external-execution classification; bounded
   metadata-only response; opt-in closable UI; no automatic conflict resolution or mutation.
3. **Verification — passed on PR #174 exact head:** backend/frontend, Playwright daily-use and
   axe on desktop/mobile, CodeQL, Dependency Review, v0.4 Hardening Gates and Platform
   Readiness. Post-merge main CI, CodeQL and Platform Readiness also passed. Provider smoke
   was skipped by workflow configuration and is not counted as a pass.
4. **External pilot — not done:** only with explicit owner consent and a non-sensitive fixture,
   compare ordinary chat summary versus a verified checkpoint in two actual clients and note
   recoverability/error rates. Private external-client artifacts are **not** authorized for
   publication by this RFC.
5. **PAI-005 remains separate:** writeable Task/Decision/Outcome lifecycle transitions require
   their own accepted design and must not be smuggled into this read-only preview.

## Promotion rule

PAI-004 is completed for the read-only metadata API in PR #170. PAI-034 is completed in
PR #174 after the reviewed merge and exact-head deterministic gates. Its scope remains
read-only and metadata-only; semantic cross-source reconciliation, external pilot and
writeable lifecycle transitions are not included. PAI-005 remains a separate design track.
