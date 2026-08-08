"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiJson, SseEvent, streamSse } from "@/lib/api";

type Provider = { id: string; configured: boolean; models: string[] };
type Project = { id: string; name: string; description: string };
type Conversation = {
  id: string;
  title: string;
  provider: string;
  model: string;
  project_id?: string;
  created_at: string;
  updated_at: string;
};
type PersistedMessage = {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
};
type UiMessage = { id?: string; role: "user" | "assistant" | "system"; content: string };
type ConversationDetail = {
  conversation: Conversation;
  messages: PersistedMessage[];
  execution_events: SseEvent[];
};
type MCPConnector = {
  id: string;
  name: string;
  enabled: boolean;
  allowed_tools: string[];
  connection_status: "disabled" | "configured" | "connected" | "error";
};

const ACTIVE_CONVERSATION_KEY = "personal-ai-os.active-conversation";

export function ChatWorkspace() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [connectors, setConnectors] = useState<MCPConnector[]>([]);
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("");
  const [project, setProject] = useState("general");
  const [projectFilter, setProjectFilter] = useState("all");
  const [conversationId, setConversationId] = useState<string>();
  const [input, setInput] = useState("");
  const [useMcp, setUseMcp] = useState(false);
  const [connectorId, setConnectorId] = useState("local-reference");
  const [toolName, setToolName] = useState("system.echo");
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [trace, setTrace] = useState<SseEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);

  useEffect(() => {
    void Promise.all([
      apiJson<{ items: Provider[] }>("/api/providers"),
      apiJson<{ items: Project[] }>("/api/projects"),
      apiJson<{ default_provider: string; default_model: string }>("/api/settings"),
      apiJson<{ items: Conversation[] }>("/api/conversations"),
      apiJson<{ items: MCPConnector[] }>("/api/mcp/connectors"),
    ])
      .then(async ([providerData, projectData, settings, conversationData, connectorData]) => {
        setProviders(providerData.items);
        setProjects(projectData.items);
        setProvider(settings.default_provider);
        setModel(settings.default_model);
        setConversations(conversationData.items);
        setConnectors(connectorData.items);
        const savedId = window.localStorage.getItem(ACTIVE_CONVERSATION_KEY);
        if (savedId) {
          try {
            await openConversation(savedId);
          } catch {
            window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
          }
        }
      })
      .catch(() =>
        setMessages([
          {
            role: "system",
            content: "The API is not reachable yet. Start the FastAPI service and refresh.",
          },
        ]),
      );
  }, []);

  const selectedProvider = useMemo(
    () => providers.find((item) => item.id === provider),
    [provider, providers],
  );
  const selectedConnector = useMemo(
    () => connectors.find((item) => item.id === connectorId),
    [connectorId, connectors],
  );

  function selectConnector(id: string) {
    setConnectorId(id);
    const connector = connectors.find((item) => item.id === id);
    setToolName(id === "local-reference" ? "system.echo" : connector?.allowed_tools[0] || "");
  }

  async function loadConversations(filter = projectFilter) {
    const query = filter === "all" ? "" : `?project_id=${encodeURIComponent(filter)}`;
    const data = await apiJson<{ items: Conversation[] }>(`/api/conversations${query}`);
    setConversations(data.items);
  }

  async function openConversation(id: string) {
    setLoadingConversation(true);
    try {
      const detail = await apiJson<ConversationDetail>(`/api/conversations/${id}`);
      setConversationId(detail.conversation.id);
      setProvider(detail.conversation.provider);
      setModel(detail.conversation.model);
      setProject(detail.conversation.project_id || "general");
      setMessages(
        detail.messages.map((item) => ({
          id: item.id,
          role: item.role === "user" || item.role === "assistant" ? item.role : "system",
          content: item.content,
        })),
      );
      setTrace(detail.execution_events);
      window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, detail.conversation.id);
    } finally {
      setLoadingConversation(false);
    }
  }

  async function createConversation() {
    if (!model || running) return;
    const created = await apiJson<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ provider, model, project_id: project, title: "New conversation" }),
    });
    setConversationId(created.id);
    setMessages([]);
    setTrace([]);
    window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, created.id);
    await loadConversations();
  }

  function selectProvider(id: string) {
    const next = providers.find((item) => item.id === id);
    setProvider(id);
    setModel(next?.models[0] || "");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || !model || running) return;
    setMessages((current) => [
      ...current,
      { role: "user", content },
      { role: "assistant", content: "" },
    ]);
    setInput("");
    setRunning(true);
    try {
      await streamSse(
        "/api/chat/stream",
        {
          conversation_id: conversationId,
          provider,
          model,
          project_id: project,
          content,
          tool: useMcp
            ? {
                name: toolName,
                connector_id: connectorId === "local-reference" ? null : connectorId,
                arguments: { message: content },
              }
            : null,
        },
        (item) => {
          setTrace((current) => [...current, item]);
          if (item.type === "message") {
            const delta = String(item.payload.delta || "");
            setMessages((current) =>
              current.map((message, index) =>
                index === current.length - 1
                  ? { ...message, content: message.content + delta }
                  : message,
              ),
            );
          }
          if (item.type === "error") {
            const detail = String(item.payload.message || "Execution failed");
            setMessages((current) =>
              current.map((message, index) =>
                index === current.length - 1 ? { role: "system", content: detail } : message,
              ),
            );
          }
          if (item.type === "done" && typeof item.payload.conversation_id === "string") {
            const id = item.payload.conversation_id;
            setConversationId(id);
            window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, id);
          }
        },
      );
      await loadConversations();
    } catch (error) {
      setMessages((current) =>
        current.map((message, index) =>
          index === current.length - 1
            ? {
                role: "system",
                content: error instanceof Error ? error.message : "Stream failed",
              }
            : message,
        ),
      );
    } finally {
      setRunning(false);
    }
  }

  const history = (
    <div className="space-y-3">
      <div className="flex gap-2">
        <select
          className="field min-w-0 flex-1"
          value={projectFilter}
          onChange={(event) => {
            const next = event.target.value;
            setProjectFilter(next);
            void loadConversations(next);
          }}
          aria-label="Filter conversations by project"
        >
          <option value="all">All projects</option>
          {projects.map((item) => (
            <option key={item.id} value={item.id}>{item.name}</option>
          ))}
        </select>
        <button className="button-primary px-4" onClick={() => void createConversation()} disabled={!model || running}>
          New
        </button>
      </div>
      <div className="max-h-[540px] space-y-2 overflow-y-auto">
        {conversations.length === 0 && (
          <p className="rounded-2xl bg-black/[0.025] p-4 text-sm text-muted">No conversations yet.</p>
        )}
        {conversations.map((item) => (
          <button
            key={item.id}
            className={`w-full rounded-2xl p-4 text-left transition ${
              item.id === conversationId ? "bg-ink text-white" : "bg-white/55 hover:bg-white"
            }`}
            onClick={() => void openConversation(item.id)}
            disabled={running || loadingConversation}
          >
            <span className="block truncate text-sm font-semibold">{item.title}</span>
            <span className={`mt-1 block text-xs ${item.id === conversationId ? "text-white/65" : "text-muted"}`}>
              {item.project_id || "general"} · {new Date(item.updated_at).toLocaleString()}
            </span>
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="space-y-5">
      <details className="panel p-4 xl:hidden">
        <summary className="cursor-pointer text-sm font-semibold">Conversation history</summary>
        <div className="mt-4">{history}</div>
      </details>
      <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
        <aside className="panel hidden h-fit p-4 xl:block">
          <p className="eyebrow mb-4">Conversations</p>
          {history}
        </aside>
        <section className="panel flex min-h-[620px] flex-col overflow-hidden">
          <div className="grid gap-3 border-b border-black/5 p-4 sm:grid-cols-3">
            <label className="text-xs font-semibold text-muted">Provider
              <select className="field mt-2 w-full" value={provider} onChange={(event) => selectProvider(event.target.value)}>
                {providers.map((item) => (
                  <option key={item.id} value={item.id}>{item.id} · {item.configured ? "ready" : "key needed"}</option>
                ))}
              </select>
            </label>
            <label className="text-xs font-semibold text-muted">Model
              <select className="field mt-2 w-full" value={model} onChange={(event) => setModel(event.target.value)}>
                {(selectedProvider?.models || []).map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <label className="text-xs font-semibold text-muted">Project
              <select className="field mt-2 w-full" value={project} disabled={Boolean(conversationId)} onChange={(event) => setProject(event.target.value)}>
                {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
          </div>
          <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6" aria-live="polite">
            {loadingConversation && <p className="text-sm text-muted">Restoring conversation...</p>}
            {!loadingConversation && messages.length === 0 && (
              <div className="mx-auto mt-20 max-w-md text-center">
                <div className="mx-auto mb-5 grid size-14 place-items-center rounded-3xl bg-accent/10 text-sm font-bold text-accent">AI</div>
                <h2 className="text-2xl font-semibold tracking-tight">One workspace, many models.</h2>
                <p className="mt-3 text-sm leading-6 text-muted">Open a saved conversation or start a new one. History and execution events survive service restarts.</p>
              </div>
            )}
            {messages.map((message, index) => (
              <article key={message.id || index} className={`max-w-[88%] rounded-3xl px-5 py-4 text-sm leading-6 ${message.role === "user" ? "ml-auto bg-ink text-white" : message.role === "system" ? "bg-red-50 text-red-800" : "bg-black/[0.035] text-ink"}`}>
                {message.content || <span className="animate-pulse text-muted">Thinking...</span>}
              </article>
            ))}
          </div>
          <form onSubmit={submit} className="border-t border-black/5 p-4">
            <textarea className="min-h-24 w-full resize-none rounded-3xl border border-black/10 bg-white/70 p-4 text-sm outline-none focus:border-accent" placeholder="Ask, plan, or execute..." value={input} onChange={(event) => setInput(event.target.value)} />
            <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
              <div className="flex flex-1 flex-wrap items-end gap-2">
                <label className="flex min-h-11 items-center gap-2 rounded-2xl bg-black/[0.035] px-4 text-xs font-medium text-muted">
                  <input type="checkbox" checked={useMcp} onChange={(event) => setUseMcp(event.target.checked)} /> Use MCP tool
                </label>
                {useMcp && (
                  <>
                    <label className="min-w-44 flex-1 text-xs font-semibold text-muted">Connector
                      <select className="field mt-1 w-full" value={connectorId} onChange={(event) => selectConnector(event.target.value)}>
                        <option value="local-reference">Built-in reference</option>
                        {connectors.filter((item) => item.enabled).map((item) => (
                          <option key={item.id} value={item.id}>{item.name} · {item.connection_status}</option>
                        ))}
                      </select>
                    </label>
                    <label className="min-w-44 flex-1 text-xs font-semibold text-muted">Tool
                      <select className="field mt-1 w-full" value={toolName} onChange={(event) => setToolName(event.target.value)}>
                        {(connectorId === "local-reference" ? ["system.echo"] : selectedConnector?.allowed_tools || []).map((item) => (
                          <option key={item} value={item}>{item}</option>
                        ))}
                      </select>
                    </label>
                  </>
                )}
              </div>
              <button className="button-primary" disabled={!input.trim() || !model || running || (useMcp && !toolName)}>{running ? "Running..." : "Send"}</button>
            </div>
          </form>
        </section>
        <aside className="panel h-fit overflow-hidden">
          <div className="border-b border-black/5 p-5">
            <p className="eyebrow">Execution trace</p>
            <h2 className="mt-2 text-xl font-semibold">What happened</h2>
          </div>
          <div className="max-h-[700px] space-y-3 overflow-y-auto p-4">
            {trace.length === 0 && <p className="rounded-2xl bg-black/[0.025] p-4 text-sm leading-6 text-muted">Events show model output, tool calls, result status, and duration—never private chain-of-thought.</p>}
            {trace.map((item) => (
              <details key={item.id} className="rounded-2xl border border-black/5 bg-white/55 p-4" open={item.type === "error" || item.type === "tool_result"}>
                <summary className="cursor-pointer list-none text-sm font-semibold"><span className={`mr-2 inline-block size-2 rounded-full ${item.status === "failed" ? "bg-red-500" : item.status === "succeeded" ? "bg-emerald-500" : "bg-amber-500"}`} />{item.type.replace("_", " ")}</summary>
                <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] leading-5 text-muted">{JSON.stringify(item.payload, null, 2)}</pre>
              </details>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
