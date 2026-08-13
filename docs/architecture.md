# Architecture

```text
Next.js mobile-first web
        |
        | HTTP + SSE
        v
FastAPI application
  |-- Product profile (delivery mode + plan + capabilities)
  |-- Tenant-scoped repository
  |-- Chat orchestration
  |-- Memory service
  |-- Repository timeline
  |-- Settings facade (secret values never returned)
  |
  +-- personal_ai_os_core       generic records and project contract
  +-- personal_ai_os_providers  OpenAI / Anthropic adapters
  +-- personal_ai_os_mcp        allowlisted gateway, registry, HTTP/stdio transports
  +-- personal_ai_os_projects   General / Soccer / isolated P5 plugin registrations
        |
        v
SQLite + migration ledger
```

The application has one core and two delivery contracts. The community runtime resolves the
fixed `local` tenant and local owner. A future cloud identity adapter must resolve a real tenant
and actor before runtime creation. Cloud startup currently fails closed rather than using a
shared fallback identity.

Capability resolution is independent of UI visibility. Advanced routes enforce entitlements on
the server; hiding a control in the web application is never treated as authorization.

Chat asks the selected provider for a structured call to the single tool selected by the
user. The provider-safe function name is mapped back to the exact MCP tool ID, the gateway
checks project and connector allowlists, and the native provider tool-result protocol is
used for the final streamed answer. Only observable calls, results, status, and timing are
written to the execution trace. Tool results stay intact on the in-memory provider continuation
path, while the audit copy is recursively bounded and redacted before SSE delivery and SQLite
persistence. Historical rows are sanitized again when they are materialized through the API.

The deployable unit is one API process and one web process, with package boundaries inside one repository. SQLite is accessed through a tenant-bound repository layer so a later PostgreSQL implementation can replace it without changing core schemas.

Project plugins may contribute metadata, context, tool permissions, views, and artifact kinds. They may not alter generic core records. Removing `SoccerProject` from the registry leaves all API routes and schemas operational.

P5 uses a plugin-owned SQLite database at `data/projects/p5/p5.db` for issues, candidates,
reviews, rules, and audit events. This keeps all P5 fields outside the generic database models.
Its local MCP server is allowlisted only for the P5 project and has no shell, arbitrary path,
P3, or Codex capability.
