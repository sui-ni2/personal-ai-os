# Project State Reconciler — read-only v1 design

**Status:** PR #169 merged as `f95ee9f` and PR #170 merged as `fb9008167b013e3d19dbfc50323cbf1b4e5412e2`. PR #170 exact-head CI, v0.4 Hardening Gates, CodeQL, Dependency Review, and Platform Readiness passed; post-merge main CI also passed. The bounded read-only API v1 is implemented. No external user pilot or user-facing Projects preview has been validated; conflict classification and the UI remain future increments.
**Parent workstream:** PAI-004 in [project delivery register](project-delivery-register.md).
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

The current v1 response emits only `RECORDED` and `WORKFLOW_POSITION`. Other labels below are future classification targets, not current API output.

| Label | Meaning | Never infer |
| --- | --- | --- |
| `RECORDED` | Versioned state exists in the authoritative project store | Action executed or user verified |
| `WORKFLOW_POSITION` | Workflow `completed_steps` and `next_step` are stored | External side effect happened |
| `NEEDS_CONFIRMATION` | A claim mentions external completion but no matching trusted confirmation is available | Success from assistant prose, CI, or tool intent |
| `CONFLICT` | Versions, locks or source records disagree | Overwrite the newest or locked state |
| `INSUFFICIENT_EVIDENCE` | Missing, truncated or unverified source material prevents classification | Invent missing evidence |

A workflow with `status=completed` **only** means its own recorded steps reached the
terminal position. A separate verified external effect needs a specific receipt in the
authoritative execution/confirmation system. Public CI green is not product adoption.

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
2. **Conflict classification — future:** add stale-version, concurrent mismatch, locked
   state and insufficient-evidence classifications only with deterministic fixtures and
   explicit source/version semantics.
3. **User preview — future:** extend Projects with accessible RECORDED and
   NEEDS_CONFIRMATION presentation only after a separate reviewed increment; support
   keyboard and screen-reader behavior.
4. **API verification — passed:** focused backend regressions, CI, v0.4 Hardening Gates,
   CodeQL, Dependency Review and Platform Readiness passed on PR #170's exact head.
   Future UI work still requires TypeScript, production build, Playwright/axe and exact-head CI.
5. **External pilot — not done:** only with explicit consent and a non-sensitive fixture,
   compare ordinary chat summary versus a verified checkpoint in two actual clients and
   note recoverability/error rates. Private external-client artifacts are **not** authorized
   for publication by this RFC.

## Promotion rule

PAI-004 becomes `active` only after a scoped branch/PR exists and the implementation
is checked for overlap with #169. It becomes `completed` only after a reviewed merge,
matching exact-SHA deterministic gates, and a clear statement of the remaining external
limitations. PAI-005 remains a separate design track for writeable lifecycle transitions.
