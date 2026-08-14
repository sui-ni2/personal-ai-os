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

The repository already ignores SQLite databases and additionally ignores common private-state directories.

## Isolation model

State is always keyed by `project_id`. Sharing the persistence engine does **not** mean sharing project data.

For example, two projects may both use the namespaces below while keeping their actual values isolated:

```text
project A
  workflow/current
  formal/latest
  history/review
  experience/*

project B
  workflow/current
  formal/latest
  history/review
  experience/*
```

A project only receives state whose `project_id` matches the active conversation project.

## State vs experience

State is current, replaceable truth. Writing the same `(project_id, namespace, key)` updates the existing current value.

Experience is append-only evidence. Multiple observations may coexist and be supplied to the model as project-scoped historical context.

This distinction prevents a daily observation from silently replacing a durable workflow state or a prior formal record.

## Chat continuity

At request time the API constructs provider input from:

1. project configuration
2. project-scoped persistent state
3. the current conversation history

Persistent state is injected as system-side runtime data. It does not become part of the visible conversation transcript and cannot override higher-priority policy. Missing state is never fabricated.

## API

```text
GET  /api/projects/{project_id}/state
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
  "confidence": 1.0
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

## Privacy rule

Do not add project-specific private values to examples, fixtures, documentation, commits, issues, pull requests, screenshots, or CI logs. Use synthetic examples only.
