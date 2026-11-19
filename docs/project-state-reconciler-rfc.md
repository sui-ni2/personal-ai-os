# Project State Reconciler — read-only v1 design

**Status:** read-only metadata API implementation in PR #170; not merged, not externally validated. Conflict classification and the user-facing Projects preview remain future increments.
**Parent workstream:** PAI-004 in [project delivery register](project-delivery-register.md).
**Existing implementation to reuse:** [persistent project state](persistent-project-state.md), [bounded handoff](project-handoff.md), [recovery](project-handoff.md#restart-recovery), and the Project Control Center.

## Problem

The application persists tasks, decisions, outcomes, workflow positions, reviewed memory,
and recovery evidence. However, a persisted record, a workflow marked completed, a model
statement, and a confirmed external action are **different kinds of evidence**. Collapsing
them into one checkmark can mislead a user resuming a long-running project.

PR #169 removes unconditional UI completion checkmarks and adds a bounded list of next
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

## Proposed contract (metadata only)

An opt-in endpoint such as
`GET /api/projects/{project_id}/reconciliation-preview?limit=20` would read existing
authoritative project-scoped stores. The exact route/name is subject to implementation
review; do not add a second private state database.

Suggested response fields:

- `project_id`, `read_at`, `state_fingerprint` (no private state values), and
  `truncated` plus **original total counts**;
- `recorded_workflows`: active/completed/other counts sourced solely from the workflow store;
- `next_steps`: bounded workflow ID, run key, exact version, and next recorded step;
- `items`: bounded state namespace/key/version and a *reason-coded* evidence label;
- `needs_user_review`: true when evidence is incomplete, conflicting, or involves a
  non-idempotent external side effect.

The response must never contain provider credentials, raw conversations, chain-of-thought,
tool payload bodies, unreviewed memory values, prior transition evidence, authorization
headers, or another project's storage records. Only actor-authorized metadata is eligible.

## Evidence classification (invariants)

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

1. **Pure classifier and tests:** implement deterministic inputs/outputs in an independent
   module, with synthetic data only. Tests include absent evidence, stale versions,
   concurrent version mismatch, terminal workflow without external receipt, unknown
   external effect, locked state, project/tenant isolation and truncation.
2. **Read-only API:** wire the classifier behind the existing access middleware, preserve
   response-size limits, and verify no state or audit writes occur on GET.
3. **User preview:** extend Projects only after PR #169 has settled, distinguish
   `RECORDED` and `NEEDS_CONFIRMATION`, support keyboard/screen-reader behavior.
4. **Verification:** focused backend regressions, TypeScript and production build,
   Playwright/axe, CodeQL, dependency review and exact-head CI. A mock success does not
   prove real-world reconciliation.
5. **External pilot:** only with explicit consent and a non-sensitive fixture, compare
   ordinary chat summary versus a verified checkpoint in two actual clients and note
   recoverability/error rates. A separate Skill candidate is **not** authorized for
   publication by this RFC.

## Promotion rule

PAI-004 becomes `active` only after a scoped branch/PR exists and the implementation
is checked for overlap with #169. It becomes `completed` only after a reviewed merge,
matching exact-SHA deterministic gates, and a clear statement of the remaining external
limitations. PAI-005 remains a separate design track for writeable lifecycle transitions.
