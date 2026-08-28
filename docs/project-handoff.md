# Project handoff snapshots

Personal AI OS exposes a read-only handoff surface for continuing a project in a new conversation or client without treating chat-window history as the source of truth.

## API

```text
GET /api/projects/{project_id}/handoff
GET /api/projects/{project_id}/handoff?mode=compact
GET /api/projects/{project_id}/handoff?mode=full
```

`compact` is the default. Both modes are bounded.

## Compact handoff

The compact form is intended for routine continuation. It includes current project-scoped state, recent project experience, and recent workflow positions, but strips fields that are not needed to resume the work.

Limits:

- 20 current state records
- 20 recent experience records
- 10 recent workflow runs

Compact state records keep namespace, key, value, version, status, and update time. Compact workflow records keep the current/next/completed step position and version/status. Sources and workflow step definitions are omitted from the compact form.

## Full handoff

The full form keeps the richer current records already available through the private state/workflow APIs, but remains bounded:

- 200 current state records
- 200 recent experience records
- 100 recent workflow runs

The response includes total record counts and `truncated=true` when any limit is exceeded.

`full` means richer current-state detail; it does **not** mean an unbounded export.

## Deliberate exclusions

Neither handoff mode includes:

- project state history;
- workflow transition receipts or transition evidence;
- provider credentials, tokens, cookies, or sessions;
- raw provider conversations outside the normal conversation API;
- generic Memory records from another surface;
- another project's private state.

A handoff is assembled from the same physically isolated per-project SQLite store already used by persistent project state and workflow gates. It does not create a second copy of project state and does not write a new audit payload containing the private values.

## Security and privacy boundary

The route is served by the same application and access middleware as the existing private project-state APIs. Unknown project IDs fail closed with HTTP 404, and unsupported handoff modes fail validation.

The handoff feature does not automate third-party account switching or authentication. It only packages Personal AI OS project continuity data that the caller is already authorized to read.

## Remaining roadmap work

This API provides the data contract for compact/full handoff snapshots. A dedicated UI handoff form, explicit crash/restart recovery workflow, and any external-client adapter remain separate work and must preserve the same project-isolation and privacy boundaries.
