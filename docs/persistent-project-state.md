# Persistent Project State

Personal AI OS uses a domain-neutral persistent project state layer so a model can resume work across conversations without relying on chat-window memory alone.

## Boundary

The public repository contains only the protocol, API, storage adapter, context resolver, workflow engine, tests, and documentation.

Real user state is runtime data. It belongs in local/private storage and must not be committed to Git:

- current workflow stage
- formal/locked decisions
- daily records
- review history
- experience ledgers
- private project strategy
- workflow step names and receipts when they reveal private operating logic
- user uploads or purchase records
- provider credentials, tokens, cookies, or secrets

The repository ignores SQLite databases and common private-state directories.

## Physical project isolation

Project state is not stored in the generic Memory table. Each project gets a physically separate private SQLite database under the runtime data directory:

```text
data/private/p/<tenant-scope>/<opaque-project-key>/s.db
```

The `opaque-project-key` is a compact one-way key derived from a validated project ID; a raw
project ID is never embedded in a new storage path. Existing pre-v0.4 databases under
`data/private/project-state/<tenant-scope>/<project-id>/state.sqlite3` are discovered only inside
that fixed legacy root, copied into the new private location on first use, and left in place as a
rollback source. A project database contains only that project's current state, version history,
experience ledger, workflow runs, and transition receipts.

Sharing the persistence engine does **not** mean sharing project data. For example:

```text
project A private DB
  state/*
  state_history/*
  experience/*
  workflows/*

project B private DB
  state/*
  state_history/*
  experience/*
  workflows/*
```

A model receives only state and workflow context from the active conversation's `project_id`.

## State vs experience

State is current, replaceable truth. Writing the same `(project_id, namespace, key)` creates a new version while retaining the prior value in private history.

Experience is append-only evidence. Multiple observations may coexist and be supplied to the model as project-scoped historical context.

This distinction prevents a daily observation from silently replacing a durable workflow state or a prior formal record.

## Formal locks

A state write may set `lock=true`. Once locked, the current value cannot be overwritten by an ordinary write.

Replacing a locked value requires all of the following:

1. an explicit `supersede_locked=true`
2. the caller's `expected_version` matching the current version
3. a new state version being created while the previous locked value is preserved in private history

This protects formal/final records from accidental same-day rewrites and stale chat windows.

## Cross-window concurrency

State writes support `expected_version` optimistic concurrency.

If two windows both read version 3 and one advances the state to version 4, a later write from the stale window using `expected_version=3` fails with HTTP 409 instead of overwriting the newer state.

Workflow transitions use the same rule. A stale window cannot advance an old workflow version after another window has moved the run forward.

Window memory is therefore advisory; persistent project state is the transaction boundary.

## Strict workflow gates

A project may create a private workflow run with an ordered list of steps. The generic engine does not know what those steps mean.

Example using synthetic names only:

```json
{
  "workflow_id": "daily",
  "run_key": "synthetic-run",
  "steps": ["review", "input", "formal", "complete"],
  "source": "local-workflow"
}
```

A new run starts before the first step. The engine exposes:

- `completed_steps`
- `current_step`
- `next_step`
- `version`
- `status`

The caller may advance only to the exact `next_step`. Skipping directly from `review` to `formal` fails closed with HTTP 409.

Each successful transition stores an append-only private receipt containing the step, source, evidence payload, version, and timestamp. Completed workflows cannot be advanced again.

This makes a daily sequence enforceable instead of relying on a prompt that merely says what should happen next.

## Chat continuity

At request time the API constructs provider input from:

1. project configuration
2. project-scoped persistent state
3. project-scoped workflow gates
4. the current conversation history

Persistent state and workflow state are injected as system-side runtime data. They do not become part of the visible conversation transcript and cannot override higher-priority policy. Missing state is never fabricated.

The workflow system message explicitly tells the model not to claim a later step is complete unless it appears in `completed_steps`, and not to silently skip the required `next_step`.

The state context snapshot is bounded before it is sent to the provider. If the private state exceeds the context budget, older experience/state entries are omitted and `truncated=true` is supplied rather than emitting malformed JSON.

## API

State and experience:

```text
GET  /api/projects/{project_id}/state
GET  /api/projects/{project_id}/state/history
PUT  /api/projects/{project_id}/state/records
POST /api/projects/{project_id}/state/experience
```

Workflow gates:

```text
GET  /api/projects/{project_id}/workflows
POST /api/projects/{project_id}/workflows
GET  /api/projects/{project_id}/workflows/{workflow_id}/{run_key}
POST /api/projects/{project_id}/workflows/{workflow_id}/{run_key}/advance
GET  /api/projects/{project_id}/workflows/{workflow_id}/{run_key}/transitions
```

A state record uses a generic shape:

```json
{
  "namespace": "workflow",
  "key": "current",
  "value": {"stage": "review_done"},
  "source": "local-workflow",
  "confidence": 1.0,
  "lock": false,
  "expected_version": 2,
  "supersede_locked": false
}
```

A formal-style synthetic record can be locked:

```json
{
  "namespace": "formal",
  "key": "latest",
  "value": {"status": "final"},
  "source": "local-workflow",
  "confidence": 1.0,
  "lock": true,
  "expected_version": 0
}
```

An experience record uses:

```json
{
  "namespace": "review",
  "text": "Verified prior records should outrank reconstruction.",
  "source": "local-review",
  "confidence": 0.9
}
```

A workflow transition uses:

```json
{
  "next_step": "review",
  "expected_version": 1,
  "evidence": {"receipt": "synthetic-reference"},
  "source": "local-workflow"
}
```

## Domain adapters

Soccer, P5, and future long-running projects may share this engine while defining their own private namespaces, step names, receipts, and workflow semantics outside the generic core.

The core must not contain real domain strategies or user data. Domain adapters must not read another project's private database.

## What this does and does not solve

This layer removes the need for a Personal AI OS conversation to rely on its own window history as the source of truth. A new conversation in the same project receives the saved private state and workflow position.

It does **not** change the native memory implementation of third-party chat applications by itself. An external client only benefits from these records when it is connected to the Personal AI OS state surface or another approved adapter. The private runtime database remains the source of truth either way.

## Privacy rule

Do not add project-specific private values to examples, fixtures, documentation, commits, issues, pull requests, screenshots, or CI logs. Use synthetic examples only.
