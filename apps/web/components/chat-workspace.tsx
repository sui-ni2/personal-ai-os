"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiJson, SseEvent, streamSse } from "@/lib/api";

type Provider = { id: string; configured: boolean; models: string[] };
type Project = { id: string; name: string; description: string };
type UiMessage = { role: "user" | "assistant" | "system"; content: string };

export function ChatWorkspace() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("");
  const [project, setProject] = useState("general");
  const [conversationId, setConversationId] = useState<string>();
  const [input, setInput] = useState("");
  const [useMcp, setUseMcp] = useState(false);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [trace, setTrace] = useState<SseEvent[]>([]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    void Promise.all([
      apiJson<{ items: Provider[] }>("/api/providers"),
      apiJson<{ items: Project[] }>("/api/projects"),
      apiJson<{ default_provider: string; default_model: string }>("/api/settings")
    ]).then(([providerData, projectData, settings]) => {
      setProviders(providerData.items);
      setProjects(projectData.items);
      setProvider(settings.default_provider);
      setModel(settings.default_model);
    }).catch(() => setMessages([{ role: "system", content: "The API is not reachable yet. Start the FastAPI service and refresh." }]));
  }, []);

  const selectedProvider = useMemo(() => providers.find((item) => item.id === provider), [provider, providers]);

  function selectProvider(id: string) {
    const next = providers.find((item) => item.id === id);
    setProvider(id);
    setModel(next?.models[0] || "");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || !model || running) return;
    setMessages((current) => [...current, { role: "user", content }, { role: "assistant", content: "" }]);
    setInput("");
    setTrace([]);
    setRunning(true);
    try {
      await streamSse("/api/chat/stream", {
        conversation_id: conversationId,
        provider,
        model,
        project_id: project,
        content,
        tool: useMcp ? { name: "system.echo", arguments: { message: content } } : null
      }, (item) => {
        setTrace((current) => [...current, item]);
        if (item.type === "message") {
          const delta = String(item.payload.delta || "");
          setMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, content: message.content + delta } : message));
        }
        if (item.type === "error") {
          const detail = String(item.payload.message || "Execution failed");
          setMessages((current) => current.map((message, index) => index === current.length - 1 ? { role: "system", content: detail } : message));
        }
        if (item.type === "done" && typeof item.payload.conversation_id === "string") setConversationId(item.payload.conversation_id);
      });
    } catch (error) {
      setMessages((current) => current.map((message, index) => index === current.length - 1 ? { role: "system", content: error instanceof Error ? error.message : "Stream failed" } : message));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="panel flex min-h-[620px] flex-col overflow-hidden">
        <div className="grid gap-3 border-b border-black/5 p-4 sm:grid-cols-3">
          <label className="text-xs font-semibold text-muted">Provider
            <select className="field mt-2 w-full" value={provider} onChange={(event) => selectProvider(event.target.value)}>
              {providers.map((item) => <option key={item.id} value={item.id}>{item.id} · {item.configured ? "ready" : "key needed"}</option>)}
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
          {messages.length === 0 && (
            <div className="mx-auto mt-20 max-w-md text-center">
              <div className="mx-auto mb-5 grid size-14 place-items-center rounded-3xl bg-accent/10 text-2xl text-accent">✦</div>
              <h2 className="text-2xl font-semibold tracking-tight">One workspace, many models.</h2>
              <p className="mt-3 text-sm leading-6 text-muted">Choose a provider and project. Conversation history stays intact when the provider changes.</p>
            </div>
          )}
          {messages.map((message, index) => (
            <article key={index} className={`max-w-[88%] rounded-3xl px-5 py-4 text-sm leading-6 ${message.role === "user" ? "ml-auto bg-ink text-white" : message.role === "system" ? "bg-red-50 text-red-800" : "bg-black/[0.035] text-ink"}`}>
              {message.content || <span className="animate-pulse text-muted">Thinking…</span>}
            </article>
          ))}
        </div>
        <form onSubmit={submit} className="border-t border-black/5 p-4">
          <textarea className="min-h-24 w-full resize-none rounded-3xl border border-black/10 bg-white/70 p-4 text-sm outline-none focus:border-accent" placeholder="Ask, plan, or execute…" value={input} onChange={(event) => setInput(event.target.value)} />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <label className="flex min-h-11 items-center gap-2 rounded-2xl bg-black/[0.035] px-4 text-xs font-medium text-muted">
              <input type="checkbox" checked={useMcp} onChange={(event) => setUseMcp(event.target.checked)} /> Verify MCP trace
            </label>
            <button className="button-primary" disabled={!input.trim() || !model || running}>{running ? "Running…" : "Send"}</button>
          </div>
        </form>
      </section>
      <aside className="panel h-fit overflow-hidden">
        <div className="border-b border-black/5 p-5">
          <p className="eyebrow">Execution trace</p>
          <h2 className="mt-2 text-xl font-semibold">What happened</h2>
        </div>
        <div className="space-y-3 p-4">
          {trace.length === 0 && <p className="rounded-2xl bg-black/[0.025] p-4 text-sm leading-6 text-muted">Events will show model output, tool calls, result status, and duration—never private chain-of-thought.</p>}
          {trace.map((item) => (
            <details key={item.id} className="rounded-2xl border border-black/5 bg-white/55 p-4" open={item.type === "error" || item.type === "tool_result"}>
              <summary className="cursor-pointer list-none text-sm font-semibold"><span className={`mr-2 inline-block size-2 rounded-full ${item.status === "failed" ? "bg-red-500" : item.status === "succeeded" ? "bg-emerald-500" : "bg-amber-500"}`} />{item.type.replace("_", " ")}</summary>
              <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] leading-5 text-muted">{JSON.stringify(item.payload, null, 2)}</pre>
            </details>
          ))}
        </div>
      </aside>
    </div>
  );
}
