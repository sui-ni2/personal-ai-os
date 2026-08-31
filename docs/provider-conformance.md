# Provider conformance and fallback

Every provider adapter is assessed against the same application contract:

- allowlisted models; configured/not-configured state; streaming; cancellation;
  timeout; bounded retry; rate-limit and authentication classification;
- tool-call and structured-output boundary; file/image capability is explicitly
  unavailable until an adapter implements it; and
- usage is recorded as `EXACT`, `ESTIMATED`, or `UNKNOWN`, never silently
  presented as a bill.

The community runtime exposes three fallback policies:

| Policy | Behavior |
| --- | --- |
| `STRICT_PROVIDER` | Never switch automatically. |
| `FALLBACK_ALLOWED` | A retryable pre-output failure may use the explicitly configured fallback provider/model. |
| `ASK_BEFORE_FALLBACK` | A caller must set an explicit fallback confirmation for a retryable pre-output failure. |

Fallback retains only the workspace's project, tasks, decisions, outcomes,
reviewed memory, file references, and authorized context. It never copies a
provider session, credentials, private thread state, or hidden reasoning. A
request with a tool action never falls back automatically: any ambiguous
external effect stays `OUTCOME_UNKNOWN` or requires a new confirmation.

`MOCK_CONTRACT_TEST != REAL_PROVIDER_VALIDATION`. Real provider smoke remains
an external release gate when credentials are deliberately configured.
