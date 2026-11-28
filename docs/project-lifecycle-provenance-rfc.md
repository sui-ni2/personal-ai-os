# PAI-005 — Task / Decision / Outcome lifecycle provenance

Status: proposed; owner review required. No writable lifecycle feature is implemented. PAI-005 stays in the design lane until accepted. Preserve PAI-003 neutral Recorded labels and PAI-004/034 read-only reconciliation. PR #183 fixes an existing editor defect independently.

## Problem and scope

The current Control Center edits generic versioned state records. A summary, a saved record, a terminal workflow cursor, a user decision and a verified external effect are distinct. Neither the generic replacement PUT nor its caller-supplied source can represent an authorized acceptance receipt. The goal is to resume work with explicit provenance, not to create a second persistence engine.

Reuse project identity, private SQLite isolation, version history, workflow and governed execution metadata. No new provider, Memory consent change, private material publication, or external action.

## Proposed lifecycle contract

| Kind | Initial | Permitted transitions |
| --- | --- | --- |
| Task | planned | planned -> active/cancelled; active -> blocked/submitted/cancelled; blocked -> active/cancelled; submitted -> accepted/active; accepted -> active only with explicit reopen and reason |
| Decision | proposed | proposed -> accepted/rejected; accepted -> superseded only with a valid accepted replacement decision in the same project |
| Outcome | draft | draft -> submitted; submitted -> accepted/draft/rejected; accepted -> superseded only with an accepted replacement outcome in the same project |

Reject unspecified transitions. Lifecycle state is separate from storage active/locked status and execution status. Cancellation/rejection is not success. No automatic cascading acceptance from task, decision, outcome or workflow. Legacy generic records remain Recorded; never infer a lifecycle state from text, namespace, lock or confidence.

## Data, evidence, permission and transaction contract

- Project-scoped opaque record ID and kind; current version, lifecycle state and bounded immutable transition history. Each transition records prior/new state, expected/result version, server-resolved actor, server timestamp, reason code and optional opaque evidence references. Exact persistent representation and migration require separate review.
- Distinguish stored record, user-attested acceptance of a particular version, authoritative external receipt with resolved scope/status, and independent external validation. User acceptance does not imply external execution. Free-text evidence, model output, caller-supplied source, invocation intent and CI are not external proof.
- Resolve actor/tenant/project on the server, not from body fields. Explicit user action is necessary to accept, reject, supersede or reopen an accepted record. Bind approval to exact version and intended action. Changed/expired proposals require review again; a model cannot approve its own proposal.
- Before writable implementation, enumerate all mutation paths (HTTP state PUT, MCP, direct service calls, restore/import). Generic writes must not bypass lifecycle validation. Do not attach trusted lifecycle state to arbitrary generic values. Until enforcement is demonstrated, keep the lifecycle surface read-only.
- Atomically compare expected version, validate the transition and record state plus history in the authoritative project-store transaction. Reject stale versions, invalid transitions, unauthorized locked-record supersession and cross-project references. Repeated requests must not duplicate transitions. If the result is unknown, require fresh read/review, not blind retry.
- Do not claim atomicity across different SQLite stores. Only resolve authoritative immutable same-tenant/project receipt references for a defined external action; otherwise display unverified. Unknown side effects remain NEEDS_CONFIRMATION and are never silently retried.
- Editing accepted content must not carry forward approval to a new version; retain historical receipt and require explicit reopen/review. No raw payloads, credentials, private values or actor identifiers in public Git/CI. Keep existing reconciliation metadata-only and bounded.

## Implementation slices and acceptance

1. After owner acceptance, implement a pure transition/evidence classifier and table-driven synthetic tests, with no writable route or schema change. Ambiguous/legacy records remain Recorded/unverified; classifier output is not authorization.
2. Separately review persistence and all write paths. Then implement atomic actor-bound transitions and bounded history. Tests must cover simultaneous stale writes, duplicate requests, rollback on interruption, illegal transitions, locked records, cross-project/tenant references, generic PUT/MCP bypass, approval invalidation after content edits, and backup/restore history preservation.
3. After write authorization is proven, add a small explicit review UI: keyboard/mobile operation, exact-version confirmation, visible conflict, draft retention and distinction between acceptance and external proof. No automatic approval on reload or reconciliation.
4. Require exact-head deterministic CI, code/review evidence, explicit merge decision, post-merge regression check and independent first-hand use separately. External execution requires real authoritative receipts, not fixtures.

## Owner decision

Accept or revise the transition sets, separation of user acceptance from external proof, and pure/read-only first slice. Writable storage, schema migration, approval binding and external receipt integration remain separate review decisions. Do not mark completed or promote to ready before design acceptance.
