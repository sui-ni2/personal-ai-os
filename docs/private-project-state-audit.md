# Private Project State Audit Boundary

Persistent project state is private runtime data. The generic execution trace must not become a second copy of that data.

## Data path

For project-bound state/workflow MCP tools:

1. the gateway binds the active `project_id` in trusted MCP metadata;
2. the private project database returns the raw tool result;
3. the raw result remains available on the in-memory provider continuation path so the model can use it;
4. the gateway marks that result with `metadata_only` audit policy;
5. `ExecutionEvent` sanitization replaces the private result body with an omission marker before SSE/audit persistence.

The persisted trace may contain the tool name, connector/server identity, status, duration, argument names, and the fact that a private result was omitted. It must not contain the private state value, workflow evidence payload, formal record, experience text, or other project-private result content.

## Why this is separate from secret redaction

Credential redaction and private-state suppression solve different problems.

Secret redaction detects values such as bearer tokens, API keys, passwords, cookies, and credential-shaped fields.

Private-state suppression applies even when a value is not a credential. A project formal record, daily state, candidate archive reference, or experience observation may be private user data while containing no secret-shaped string.

Therefore project-state tools use a metadata-only audit policy instead of relying on credential-pattern redaction.

## Explicit API reads

Authenticated callers that deliberately use the project state REST endpoints or invoke a project-state MCP tool receive the requested private result. That is the functional data path.

The audit boundary only prevents the generic execution-event store and trace stream from retaining an additional raw copy during model tool use.

## Provider boundary

Project state is supplied to the selected model when the user is working in that project because continuity requires the model to use it. Do not store credentials, tokens, cookies, or unrelated secrets in project state.

The persistence layer protects cross-project and audit isolation; it is not a secret vault.

## Tests

Public tests use synthetic values to verify both properties simultaneously:

- the raw project-state result is available to the model/tool caller;
- the same synthetic private value is absent from the sanitized execution event.

No real project data is used in tests or CI.
