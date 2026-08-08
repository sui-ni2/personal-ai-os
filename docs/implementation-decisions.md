# V0.1 implementation decisions

This is the narrow implementation-impacting consistency check between the product/technical specification and the Codex handoff. The source documents were not rewritten.

## Resolved without changing scope

1. **Navigation versus first milestone:** the broad information architecture names Tasks, Calendar, Journal, Reading, and Daily Report, while the handoff milestone names Chat, Trace, Memory, Repository, Projects, and Settings. V0.1 renders only the milestone modules; the other destinations remain future modules.
2. **Settings and API keys:** Settings reports provider readiness and editable non-secret preferences. Key values are read only from server-side environment variables and are never stored in SQLite or returned to the browser.
3. **MCP acceptance:** `system.echo` remains the stateless built-in reference server. External HTTP and stdio connectors are additive registry entries with exact tool allowlists, enable/disable state, discovery, timeout, and durable connection diagnostics. stdio executes only fixed argv arrays registered under server-side aliases and never accepts a shell string from the browser or model.
4. **Provider/model configuration:** provider and model IDs are supplied by backend configuration/environment variables. The UI discovers them from the API and contains no model-ID list.
5. **Repository files:** V0.1 stores artifact locators and metadata plus a durable event timeline. It does not crawl arbitrary local directories.
6. **Project set:** General and Soccer are the first registered plugins. Codex and Research are intentionally deferred because the explicit first-round request requires only General and Soccer.
7. **Streaming:** both provider text and execution status share SSE. Public event types are `message`, `tool_start`, `tool_result`, `error`, and `done`; internal database rows also retain status, duration, tool name, and safe payload summaries.
8. **Conversation recovery:** conversations, messages, and execution events are queried from SQLite. The browser stores only the active conversation ID; page refresh and process restart rehydrate authoritative history from the API.
9. **Provider tool continuation:** OpenAI and Anthropic preserve their adapter boundary. Each adapter first returns one structured call for the selected allowlisted tool, then receives the tool result using its native tool-result message format before streaming the final answer.

## Non-negotiable boundaries retained

- No Soccer-specific fields in core Chat, Memory, Repository, Model Router, or execution-event schemas.
- No raw private chain-of-thought.
- No committed secrets.
- No HealthKit, full calendar sync, multi-user collaboration, or microservices in V0.1.
