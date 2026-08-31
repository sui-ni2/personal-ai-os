# Product roadmap

Personal AI OS has published its first stable community/self-hosted release, `v0.2.0`. The core first-use loop is verified: the community edition can start safely without credentials, connect a supported AI service, persist a default provider/model, complete text conversations, retain project/conversation state across restart, and expose tools and reviewed memory without binding that state to one model provider.

The stable release was published only after the documented real-inference, restart/persistence, CI, security, Windows/container/mobile, and privacy/artifact gates passed. Future releases remain fail-closed against the same evidence standard.

## Current product contract

1. **One Personal AI workspace, replaceable AI services**
   - Projects, context, reviewed memory, tools, and execution history belong to the workspace.
   - OpenAI, Anthropic, and optional local Ollama use one provider-independent application contract.
   - Provider-specific details remain behind adapters and Advanced Settings.
2. **Local-first community edition**
   - FastAPI/SQLite and the web client run locally with server-side credential boundaries.
   - Community/self-hosted is the runnable delivery mode today.
   - Managed cloud remains fail-closed until account identity, tenant isolation, billing, export, and deletion are real.
3. **Simple by default, inspectable when needed**
   - Standard mode keeps routine model, project, and chat work simple.
   - Advanced mode exposes MCP, provider, repository, memory, and execution controls.
4. **Continuity before feature count**
   - Restart-safe conversations, project-scoped state, workflow gates, version history, outcomes, and MCP continuity are more important than adding disconnected features.

## Next priorities after v0.2.0

1. **Prove workspace continuity with external users**
   - Fresh-install tests on Windows.
   - Real provider/model switching while project and task state remain continuous.
   - External issue/PR feedback instead of synthetic adoption signals.
2. **Strengthen Project Continuity**
   - Make Tasks, Conversations, Files, Outcomes, decisions, changed files, blockers, and reviewed Project Memory first-class project state.
   - Compact/full read-only handoff snapshots, explicit Projects-screen preview, metadata-only interruption detection, and user-confirmed restart recovery are implemented with bounded payloads and no provider-session copying.
3. **Finish the Settings center**
   - Unify AI services, default models, voice, memory/privacy, appearance, data controls, MCP, and diagnostics.
   - Keep credential values server-side and never return them to the browser.
4. **Improve recovery, routing, privacy, and cost controls**
   - Provider fallback, draft recovery, explicit side-effect confirmation, send-scope receipts, budgets, and usage ledgers.
5. **Expand provider choice deliberately**
   - Add Gemini and carefully scoped compatible endpoints only when their adapter and failure semantics are tested.
6. **Complete voice end to end**
   - Harden push-to-talk and transcription, then spoken replies, interruption, and continuous conversation.
7. **Package the community edition**
   - Windows installation/update path, crash recovery, accessibility, mobile checks, and signed artifacts when the release process is mature enough.
8. **Grow maintainership, not vanity metrics**
   - Convert real tester friction into focused issues, small PRs, release notes, and reproducible maintenance evidence.

Progress is demonstrated through working releases, real-inference checks, reproducible user feedback, and auditable maintenance—not feature count or manufactured engagement.
