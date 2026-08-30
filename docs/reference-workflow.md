# Reference workflow: long-running research or build work

This provider-neutral example demonstrates the Personal AI OS thesis using only non-sensitive sample data. It is intentionally not a Soccer, P3, or P5 workflow.

1. Create a Project such as `Long-running research` or `Release hardening`.
2. Record a Task (`task/next`), a Decision (`decision/scope`), an Outcome (`outcome/draft`), and a File/change reference (`file/notes`) through the project-state surface.
3. Add a reviewed Memory entry only after it is worth carrying forward.
4. Create a workflow with explicit steps such as `gather → review → publish`; advance only the required next step with evidence.
5. Invoke the allowlisted local `system.echo` Tool for the project (or an already-configured, explicitly allowed connector) with non-sensitive input. When a configured provider is available, inspect the resulting Chat execution trace and the bounded `tool.completed` Activity record. Do not add credentials merely to demonstrate this optional step.
6. Use the repository Activity view to inspect that project actions occurred without exposing private state values in generic audit events.
7. Inspect the bounded Continuity snapshot before moving to another conversation or client.
8. After an interrupted session, preview persisted state and explicitly confirm recovery. Resume from current persisted state; do not infer completed work from chat history.

Providers can execute messages, but they do not own this state. The source of truth is the tenant-scoped project store: current Task/Decision/Outcome/File records, reviewed project Memory, workflow position, and bounded execution/activity references.

The durable-state and recovery portion is reproducible with the no-key commands in [5-minute evaluation](5-minute-evaluation.md). The Tool execution-trace observation is optional because it requires a provider the user has already configured; it must not be used to infer or overwrite workflow state.
