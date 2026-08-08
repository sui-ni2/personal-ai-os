"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronDown,
  History,
  MessageCircle,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  Wrench,
} from "lucide-react";
import { ActivityPanel } from "@/components/activity-panel";
import { ModelSelector, type ProviderOption } from "@/components/model-selector";
import { RichMessage } from "@/components/rich-message";
import { ErrorState } from "@/components/ui-states";
import { apiJson, type SseEvent, streamSse } from "@/lib/api";

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
type PersistedMessage = { id: string; role: "user" | "assistant" | "system" | "tool"; content: string };
type UiMessage = { id?: string; role: "user" | "assistant" | "system"; content: string };
type ConversationDetail = { conversation: Conversation; messages: PersistedMessage[]; execution_events: SseEvent[] };
type MCPConnector = {
  id: string;
  name: string;
  enabled: boolean;
  allowed_tools: string[];
  connection_status: "disabled" | "configured" | "connected" | "error";
};

const ACTIVE_CONVERSATION_KEY = "personal-ai-os.active-conversation";

function providerLabel(id: string) {
  if (id === "openai") return "OpenAI";
  if (id === "anthropic") return "Anthropic";
  return id.charAt(0).toUpperCase() + id.slice(1);
}

export function ChatWorkspace() {
  const [providers, setProviders] = useState<ProviderOption[]>([]);
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
  const [apiError, setApiError] = useState(false);
  const conversationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void Promise.all([
      apiJson<{ items: ProviderOption[] }>("/api/providers"),
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
        const requestedProject = new URLSearchParams(window.location.search).get("project");
        if (requestedProject && projectData.items.some((item) => item.id === requestedProject)) {
          setProject(requestedProject);
        }
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
      .catch(() => setApiError(true));
  }, []);

  useEffect(() => {
    conversationRef.current?.scrollTo({ top: conversationRef.current.scrollHeight, behavior: running ? "auto" : "smooth" });
  }, [messages, running]);

  const selectedProvider = useMemo(() => providers.find((item) => item.id === provider), [provider, providers]);
  const selectedConnector = useMemo(() => connectors.find((item) => item.id === connectorId), [connectorId, connectors]);

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
      setMessages(detail.messages.map((item) => ({
        id: item.id,
        role: item.role === "user" || item.role === "assistant" ? item.role : "system",
        content: item.content,
      })));
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

  async function submit(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || !model || running) return;
    setMessages((current) => [...current, { role: "user", content }, { role: "assistant", content: "" }]);
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
          tool: useMcp ? {
            name: toolName,
            connector_id: connectorId === "local-reference" ? null : connectorId,
            arguments: { message: content },
          } : null,
        },
        (item) => {
          setTrace((current) => [...current, item]);
          if (item.type === "message") {
            const delta = String(item.payload.delta || "");
            setMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, content: message.content + delta } : message));
          }
          if (item.type === "error") {
            setMessages((current) => current.map((message, index) => index === current.length - 1 ? {
              role: "system",
              content: "The request could not be completed. Check your provider or tool settings, then try again.",
            } : message));
          }
          if (item.type === "done" && typeof item.payload.conversation_id === "string") {
            const id = item.payload.conversation_id;
            setConversationId(id);
            window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, id);
          }
        },
      );
      await loadConversations();
    } catch {
      setMessages((current) => current.map((message, index) => index === current.length - 1 ? {
        role: "system",
        content: "The connection ended before the response completed. Check the service and try again.",
      } : message));
    } finally {
      setRunning(false);
    }
  }

  const history = (
    <div className="space-y-4">
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
          {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <button className="icon-button border border-line" onClick={() => void createConversation()} disabled={!model || running} aria-label="New conversation">
          <Plus aria-hidden size={18} strokeWidth={1.8} />
        </button>
      </div>
      <div className="scrollbar-subtle max-h-[calc(100vh-180px)] space-y-1.5 overflow-y-auto pr-1">
        {conversations.length === 0 && <p className="rounded-control bg-surface-subtle/55 px-3 py-4 text-sm leading-6 text-text-secondary">No conversations yet.</p>}
        {conversations.map((item) => (
          <button
            key={item.id}
            className={`w-full rounded-control px-3 py-3 text-left transition-colors duration-150 ${item.id === conversationId ? "bg-accent-soft" : "hover:bg-surface-subtle"}`}
            onClick={() => void openConversation(item.id)}
            disabled={running || loadingConversation}
            aria-current={item.id === conversationId ? "true" : undefined}
          >
            <span className="block truncate text-sm font-medium">{item.title}</span>
            <span className="mt-1 block truncate text-xs text-text-tertiary">{item.project_id || "general"} · {new Date(item.updated_at).toLocaleDateString()}</span>
          </button>
        ))}
      </div>
    </div>
  );

  if (apiError) {
    return <ErrorState title="Chat is not connected" detail="The local API is unavailable. Start the service, then refresh to restore providers, projects, and conversation history." />;
  }

  return (
    <div className="space-y-3 lg:grid lg:grid-cols-[232px_minmax(0,1fr)] lg:gap-4 lg:space-y-0">
      <details className="group panel p-3 lg:hidden">
        <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 px-2 text-sm font-medium">
          <History aria-hidden size={17} strokeWidth={1.7} />
          Conversation history
          <ChevronDown aria-hidden size={16} className="ml-auto transition-transform duration-150 group-open:rotate-180" />
        </summary>
        <div className="pt-3">{history}</div>
      </details>

      <aside className="hidden rounded-card border border-line bg-surface/55 p-3 lg:block" aria-label="Conversation history">
        <div className="mb-4 flex items-center gap-2 px-2 pt-1">
          <History aria-hidden size={16} strokeWidth={1.7} className="text-text-tertiary" />
          <h2 className="text-sm font-medium">Conversations</h2>
        </div>
        {history}
      </aside>

      <section className="panel-elevated flex h-[calc(100dvh-202px)] min-h-[610px] w-full min-w-0 flex-col overflow-hidden md:h-[calc(100vh-154px)] md:min-h-[620px] lg:h-[calc(100vh-72px)] lg:min-h-[680px]" aria-label="Chat workspace">
        <div className="flex min-h-16 flex-wrap items-center gap-1 border-b border-line bg-surface/85 px-2 py-2 sm:gap-2 sm:px-4">
          <ModelSelector
            providers={providers}
            provider={provider}
            model={model}
            onChange={(nextProvider, nextModel) => {
              setProvider(nextProvider);
              setModel(nextModel);
            }}
          />
          <label className="flex min-h-11 min-w-0 items-center gap-2 rounded-control px-3 transition-colors duration-150 hover:bg-surface-subtle">
            <MessageCircle aria-hidden size={17} strokeWidth={1.7} className="shrink-0 text-text-tertiary" />
            <span className="min-w-0">
              <span className="block text-xs text-text-tertiary">Project</span>
              <select className="block max-w-32 cursor-pointer appearance-none bg-transparent pr-4 text-sm font-medium outline-none" value={project} disabled={Boolean(conversationId)} onChange={(event) => setProject(event.target.value)} aria-label="Project context">
                {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </span>
          </label>
          <div className="ml-auto hidden items-center gap-2 px-2 text-xs text-text-secondary sm:flex">
            <span className={`status-dot ${selectedProvider?.configured ? "bg-success" : "bg-warning"}`} />
            {providerLabel(provider)} · {selectedProvider?.configured ? "Ready" : "Not configured"}
          </div>
        </div>

        <div ref={conversationRef} className="scrollbar-subtle min-h-0 flex-1 overflow-y-auto" aria-live="polite" aria-busy={running || loadingConversation}>
          <div className="mx-auto w-full max-w-[780px] px-4 py-8 sm:px-6 sm:py-10">
            {loadingConversation && (
              <div className="space-y-3" role="status" aria-label="Restoring conversation">
                <div className="skeleton h-4 w-24" /><div className="skeleton h-20 w-4/5" />
              </div>
            )}
            {!loadingConversation && messages.length === 0 && (
              <div className="mx-auto flex min-h-[360px] max-w-lg flex-col items-center justify-center text-center">
                <span className="grid size-11 place-items-center rounded-control bg-accent-soft text-accent">
                  <Sparkles aria-hidden size={19} strokeWidth={1.7} />
                </span>
                <h1 className="mt-5 text-[26px] font-medium leading-tight tracking-[-0.03em]">What would you like to explore?</h1>
                <p className="mt-3 text-sm leading-6 text-text-secondary">Ask a question, shape a plan, or continue work with your saved project context.</p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {["Help me plan today", "Summarize my next steps", "Think through a decision"].map((prompt) => (
                    <button key={prompt} type="button" className="button-secondary min-h-10 px-3 text-xs" onClick={() => setInput(prompt)}>{prompt}</button>
                  ))}
                </div>
              </div>
            )}
            <div className="space-y-8">
              {messages.map((message, index) => {
                if (message.role === "user") {
                  return <article key={message.id || index} className="ml-auto max-w-[88%] rounded-card bg-accent-soft px-4 py-3 text-sm leading-7 sm:max-w-[78%]"><RichMessage content={message.content} /></article>;
                }
                if (message.role === "system") {
                  return <article key={message.id || index} className="rounded-control border border-danger/25 bg-surface px-4 py-3 text-sm leading-6 text-danger">{message.content}</article>;
                }
                return (
                  <article key={message.id || index} className="grid grid-cols-[24px_minmax(0,1fr)] gap-3 text-[15px] text-text-primary">
                    <Sparkles aria-hidden className="mt-2 text-accent" size={17} strokeWidth={1.7} />
                    {message.content ? <RichMessage content={message.content} /> : <span className="mt-2 text-sm text-text-tertiary">Responding…</span>}
                  </article>
                );
              })}
            </div>
          </div>
        </div>

        <ActivityPanel trace={trace} />

        <form onSubmit={submit} className="bg-surface px-3 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 sm:px-5 sm:pb-5">
          {useMcp && (
            <div className="mb-2 grid gap-2 rounded-control bg-surface-subtle p-2 sm:grid-cols-2">
              <label className="text-xs font-medium text-text-secondary">
                Connector
                <select className="field mt-1 w-full" value={connectorId} onChange={(event) => selectConnector(event.target.value)}>
                  <option value="local-reference">Built-in reference</option>
                  {connectors.filter((item) => item.enabled).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.connection_status}</option>)}
                </select>
              </label>
              <label className="text-xs font-medium text-text-secondary">
                Tool
                <select className="field mt-1 w-full" value={toolName} onChange={(event) => setToolName(event.target.value)}>
                  {(connectorId === "local-reference" ? ["system.echo"] : selectedConnector?.allowed_tools || []).map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
            </div>
          )}
          <div className="mx-auto max-w-[780px] rounded-large border border-line-strong bg-surface-elevated p-2 shadow-composer focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10">
            <textarea
              className="scrollbar-subtle max-h-48 min-h-[58px] w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-6 outline-none placeholder:text-text-tertiary"
              placeholder="Ask, plan, or make something…"
              aria-label="Message"
              value={input}
              rows={2}
              onChange={(event) => setInput(event.target.value)}
            />
            <div className="flex items-center gap-1">
              <button type="button" className="icon-button" disabled title="Attachments are planned" aria-label="Attach a file (planned)">
                <Paperclip aria-hidden size={18} strokeWidth={1.7} />
              </button>
              <button type="button" className={`icon-button ${useMcp ? "bg-accent-soft text-accent" : ""}`} onClick={() => setUseMcp((current) => !current)} aria-pressed={useMcp} aria-label="Use an MCP tool">
                <Wrench aria-hidden size={18} strokeWidth={1.7} />
              </button>
              <span className="ml-1 hidden text-xs text-text-tertiary sm:inline">{useMcp ? "Tool enabled" : "Tools optional"}</span>
              <button className="button-primary ml-auto size-10 min-h-10 px-0" aria-label={running ? "Sending message" : "Send message"} disabled={!input.trim() || !model || running || (useMcp && !toolName)}>
                <Send aria-hidden size={17} strokeWidth={1.8} />
              </button>
            </div>
          </div>
        </form>
      </section>
    </div>
  );
}
