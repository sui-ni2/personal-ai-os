# v0.4 dogfooding protocol

This protocol creates adoption evidence without importing private work into the repository. Use a
dedicated local test workspace and record only a short redacted outcome receipt.

## Guardrails

- Run against a recorded package version or exact Git SHA.
- Use a synthetic project and synthetic content. Do not paste provider credentials, private files,
  medical/financial data, cookies, headers, or live user conversations.
- Never treat a mock provider, CI job, browser emulation, or unconfigured provider as real use.
- Stop on a data-integrity, privacy, confirmation, budget, or unknown-side-effect regression. Create
  a normal fix PR; do not patch `main` directly.

## Daily sequence (seven days minimum; extend to fourteen for any instability)

1. Start the app, open the same project, and verify its Control Center summary.
2. Create or advance a bounded Goal, Task, Decision, Outcome, and private project-state fixture.
3. Review send scope before each text request. Verify that the planned scope and provider receipt
   agree; do not attach unapproved files or memory.
4. Exercise a hard budget reservation and a failed/cancelled request path. Confirm no orphan
   reservation remains.
5. Use an MCP confirmation fixture: reject replay, expiry, actor/project/tool binding mismatch, and
   argument mutation. A valid concurrent consume may succeed exactly once.
6. Induce a provider fault only with a safe fixture. If an external side effect is unknown, require
   `OUTCOME_UNKNOWN` and confirm that no automatic replay occurred.
7. Restart twice. Reopen/save the project and verify state, workflow, recovery marker, usage, and
   audit/event counts remain bounded.
8. Run a compatible backup/restore fixture and inspect migration version and Doctor output.

## State-growth soak

Before release review, run the deterministic fixture to produce hundreds of synthetic state,
workflow, memory, usage, receipt, and reservation records. It must prove all of the following:

- no active orphan reservation after settlement or failure;
- no stale confirmation is accepted;
- no recovery session remains stuck after its explicit close/restore path;
- no duplicate usage record for an idempotent completion path;
- SQLite integrity is `ok` and migration receipt is intact; and
- audit/event growth is linear and bounded by the number of generated operations.

The fixture is engineering evidence only. It does not represent months of personal use.

## Redacted operator receipt

```text
date_utc:
version_or_sha:
environment: Windows version / browser only
provider: configured provider name or BLOCKED_EXTERNAL
workflow: restart | project reopen | budget | confirmation | fault | restore | doctor
result: PASS | FAIL | BLOCKED_EXTERNAL
failure_category: CODE_TEST_FAILURE | DEPENDENCY_FAILURE | PLATFORM_FAILURE | WORKFLOW_CONFIGURATION | EXTERNAL_SERVICE | INCONCLUSIVE
next_action:
```

At day 7, review all receipts. Extend through day 14 for a failure, an unreviewed external block,
or a materially changed SHA. Do not call the protocol complete merely because the calendar elapsed.
