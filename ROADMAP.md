# Product roadmap

Personal AI OS is currently an early V0.2 prototype. The goal is simple by
default and powerful when needed: an ordinary user should be able to configure
the app and complete a natural conversation within a few minutes.

## Priorities

1. **Lock the product and delivery contract**
   - Keep one core with community/self-hosted and managed cloud delivery modes.
   - Use ordinary-language defaults and keep engineering controls in Advanced Settings.
   - Preserve tenant ownership, capabilities, and plan boundaries in every new feature.
2. **Close the first-use loop**
   - Add first-run guidance, provider setup, connection checks, and model lists
     based on configured services.
   - Keep one provider-independent chat interface and make text chat reliable.
3. **Build one Settings center**
   - Bring providers, default models, voice, memory and privacy, appearance,
     language, data controls, MCP, and diagnostics into one coherent place.
4. **Simplify the workspace**
   - Keep Chat, New chat, Model, Projects, and Settings in the default experience.
   - Move Memory, MCP, provider status, logs, and repository controls into an
     advanced or developer mode.
5. **Complete projects, files, outcomes, and reviewed memory**
   - Make Tasks, Conversations, Files, Outcomes, and Project Memory first-class project areas.
   - Save useful results as versioned outcomes without silently writing long-term memory.
6. **Add recovery, routing, privacy, and cost controls**
   - Add cancellation, retry, interrupted-stream recovery, provider fallback, and draft recovery.
   - Add send-scope receipts, explicit side-effect confirmation, budgets, and usage ledgers.
7. **Complete voice end to end**
   - First deliver push-to-talk, speech-to-text, and text submission.
   - Then add spoken replies, interruption, and continuous conversation, with
     room for browser, local, and cloud voice adapters.
8. **Expand model choice**
   - Prioritize OpenAI-compatible APIs, Anthropic, Gemini, Ollama, and custom
     compatible endpoints, in that order.
9. **Prepare both delivery paths**
   - Add clear offline, missing-key, and quota guidance; privacy controls;
     Windows installation and updates; crash recovery; accessibility and mobile checks.
   - Package the community edition and run a small managed-cloud test only after account
     identity, tenant isolation, usage limits, export, and deletion pass acceptance tests.

Until the core loop is complete, broad new feature areas are lower priority.
Progress should be demonstrated through working releases and end-to-end checks,
not feature count.
