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

## Projects UI

The Projects screen exposes continuity on each active project card. It does not fetch a handoff snapshot during ordinary page load.

- `Continuity` is an explicit user action and loads the compact snapshot first.
- The snapshot is previewed before any clipboard copy action.
- Full details require a second explicit action and keep the same server-side bounds.
- The UI surfaces total counts and whether the response was truncated.
- Closing the preview discards the client-side snapshot; the UI does not persist a second handoff copy.

This makes persisted project state and workflow position inspectable again after an application restart without reconstructing missing facts from chat history.

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

## Restart recovery

Project Continuity now records metadata-only recovery sessions while a user opens a project in Chat. A checkpoint contains a fingerprint and counts for persisted state, reviewed Memory, and workflow position; it never stores a provider session, chat text, state value, transition receipt, credential, or private reasoning.

The first recovery-schema migration snapshots an existing private project database under the runtime data directory’s append-only `backups/project-recovery` area before adding recovery tables. This avoids Windows deep-path limits while preserving a recoverable copy; normal recovery never deletes or rewrites historical project state.

On restart, the detection state is exactly one of `clean`, `possibly_interrupted`, `recovery_available`, or `insufficient_evidence`. An active browser session is not called a crash: a normal window close that failed to report completion remains only `possibly_interrupted` until persisted checkpoint evidence and authoritative records are present.

`recovery_available` follows this explicit sequence: persisted checkpoint → bounded preview → user confirmation → resume from current project state. Recovery never marks unfinished work complete, never copies provider session data, and never overwrites locked or newer state. Confirmation is optimistic-concurrency protected; a stale checkpoint previews the newer persisted records with a warning.
