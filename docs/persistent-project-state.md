# Persistent Project State

Personal AI OS uses a domain-neutral persistent project state layer so a model can resume work across conversations without relying on chat-window memory alone.

## Boundary

The public repository contains only the protocol, API, storage adapter, context resolver, tests, and documentation.

Real user state is runtime data. It belongs in local/private storage and must not be committed to Git:

- current workflow stage
- formal/locked decisions
- daily records
- review history
- experience ledgers
- private project strategy
- user uploads or purchase records
- provider credentials, tokens, cookies, or secrets

The repository ignores SQLite databases and common private-state directories.

## Physical project isolation

Project state is not stored in the generic Memory table. Each project gets a physically separate private SQLite database under the runtime data directory:

```text
data/private/project-state/<tenant-scope>/<project-id>/state.sqlite3
```

The public implementation knows only the generic project ID and state protocol. A project database contains only that project's current state, version history, and experience ledger.

Sharing the persistence engine does **not** mean sharing project data. For example:

```text
project A private DB
  workflow/current
  formal/latest
  history/*
  experience/*

project B private DB
  workflow/current
  formal/latest
  history/*
  experience/*
```

A model receives only state from the active conversation's `project_id`.

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

This is the core guarantee for cross-window continuity: window memory is advisory, persistent project state is the transaction boundary.

## Chat continuity

At request time the API constructs provider input from:

1. project configuration
2. project-scoped persistent state
3. the current conversation history

Persistent state is injected as system-side runtime data. It does not become part of the visible conversation transcript and cannot override higher-priority policy. Missing state is never fabricated.

The context snapshot is bounded before it is sent to the provider. If the private state exceeds the context budget, older experience/state entries are omitted and `truncated=true` is supplied rather than emitting malformed JSON.

## API

```text
GET  /api/projects/{project_id}/state
GET  /api/projects/{project_id}/state/history
PUT  /api/projects/{project_id}/state/records
POST /api/projects/{project_id}/state/experience
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

## Domain adapters

Soccer, P5, and future long-running projects may share this engine while defining their own private namespaces and workflow semantics outside the generic core.

The core must not contain real domain strategies or user data. Domain adapters must not read another project's private database.

## Privacy rule

Do not add project-specific private values to examples, fixtures, documentation, commits, issues, pull requests, screenshots, or CI logs. Use synthetic examples only.
