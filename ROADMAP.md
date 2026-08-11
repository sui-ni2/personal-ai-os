# Product roadmap

Personal AI OS is currently an early V0.2 prototype. The goal is simple by
default and powerful when needed: an ordinary user should be able to configure
the app and complete a natural conversation within a few minutes.

## Priorities

1. **Close the core chat loop**
   - Add first-run guidance, provider setup, connection checks, and model lists
     based on configured services.
   - Keep one provider-independent chat interface and make text chat reliable.
2. **Build one Settings center**
   - Bring providers, default models, voice, memory and privacy, appearance,
     language, data controls, MCP, and diagnostics into one coherent place.
3. **Simplify the workspace**
   - Keep Chat, New chat, Model, Projects, and Settings in the default experience.
   - Move Memory, MCP, provider status, logs, and repository controls into an
     advanced or developer mode.
4. **Complete voice end to end**
   - First deliver push-to-talk, speech-to-text, and text submission.
   - Then add spoken replies, interruption, and continuous conversation, with
     room for browser, local, and cloud voice adapters.
5. **Expand model choice**
   - Prioritize OpenAI-compatible APIs, Anthropic, Gemini, Ollama, and custom
     compatible endpoints, in that order.
6. **Prepare for distribution**
   - Add clear offline, missing-key, and quota guidance; privacy controls;
     Windows installation and updates; crash recovery; accessibility and mobile
     checks; and real-user testing.

Until the core loop is complete, broad new feature areas are lower priority.
Progress should be demonstrated through working releases and end-to-end checks,
not feature count.
