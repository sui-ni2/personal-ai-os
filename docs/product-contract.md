# Product contract

## Positioning

Personal AI OS is a user-controlled AI workspace for people who manage long-running
projects across conversations, files, and devices. Its core promise is not access to more
models. It is continuity: useful context remains available, work becomes a reusable outcome,
and the user decides what enters long-term memory.

The primary loop is:

1. State a goal.
2. Authorize the relevant project context, files, and memories.
3. Complete the task with visible progress and recoverable execution.
4. Save the result as a versioned outcome.
5. Review any proposed long-term memory separately from the outcome.

## One core, two delivery modes

The community and cloud editions use one product core and one set of domain contracts.
Deployment differences are resolved through `DeploymentMode`, `PlanId`, and explicit
capabilities. Product code must not fork into separate community and cloud applications.

### Community / self-hosted

- The user supplies provider credentials or uses local models.
- Data remains in the user-controlled installation.
- MCP, plugins, custom providers, and advanced settings are available.
- The application is Apache-2.0 licensed and does not include hosted model usage.

### Cloud / managed

- A user signs in and uses platform-managed model routing, sync, and backup.
- Engineering configuration is hidden from the default experience.
- Plans grant capabilities and usage limits explicitly.
- Cloud startup must fail closed until account identity and tenant resolution are ready.

Cloud identity, billing, managed routing, and device sync are not implemented by the current
community runtime. Their capabilities in the shared contract are architectural boundaries,
not claims that those services already exist.

## User-facing language

Default surfaces use `AI service`, `Tools`, `Outcomes`, and `Activity`. Technical terms such
as Provider, MCP, Repository, token details, and execution traces belong in Advanced Settings.
Memory and Outcomes remain separate: saving an outcome never silently creates long-term memory.

## Data and entitlement boundary

Every runtime resolves one tenant and one actor before accessing core storage. The SQLite
repository automatically scopes conversations, memory, outcomes, activity, settings, and MCP
connectors to that tenant. Existing local data migrates to the `local` tenant. A cloud runtime
may not start until a real account identity service can provide this scope.

Capabilities are deny-by-default at guarded routes. The current guard covers MCP access; new
paid, managed, or advanced features must declare and enforce a capability before release.
