# Architecture

```text
Next.js mobile-first web
        |
        | HTTP + SSE
        v
FastAPI application
  |-- Chat orchestration
  |-- Memory service
  |-- Repository timeline
  |-- Settings facade (secret values never returned)
  |
  +-- personal_ai_os_core       generic records and project contract
  +-- personal_ai_os_providers  OpenAI / Anthropic adapters
  +-- personal_ai_os_mcp        allowlisted gateway and reference connector
  +-- personal_ai_os_projects   General / Soccer plugin registrations
        |
        v
SQLite + migration ledger
```

The deployable unit is one API process and one web process, with package boundaries inside one repository. SQLite is accessed through a small repository layer so a later PostgreSQL implementation can replace it without changing core schemas.

Project plugins may contribute metadata, context, tool permissions, views, and artifact kinds. They may not alter generic core records. Removing `SoccerProject` from the registry leaves all API routes and schemas operational.
