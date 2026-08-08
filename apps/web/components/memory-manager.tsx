"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiJson } from "@/lib/api";

type Memory = { id: string; type: string; text: string; source: string; confidence: number; status: "active" | "inactive"; project_id?: string; updated_at: string };

export function MemoryManager() {
  const [items, setItems] = useState<Memory[]>([]);
  const [text, setText] = useState("");
  const [source, setSource] = useState("user");

  async function load() {
    const data = await apiJson<{ items: Memory[] }>("/api/memory");
    setItems(data.items);
  }
  useEffect(() => { void load(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    await apiJson("/api/memory", { method: "POST", body: JSON.stringify({ type: "fact", text: text.trim(), source, confidence: 1, project_id: "general" }) });
    setText("");
    await load();
  }

  async function toggle(item: Memory) {
    await apiJson(`/api/memory/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: item.status === "active" ? "inactive" : "active" }) });
    await load();
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[380px_1fr]">
      <form onSubmit={create} className="panel h-fit p-5">
        <h2 className="text-xl font-semibold">Add structured memory</h2>
        <p className="mt-2 text-sm leading-6 text-muted">A memory is only durable when it has content, source, status, and an audit record.</p>
        <label className="mt-6 block text-xs font-semibold text-muted">Source<input className="field mt-2 w-full" value={source} onChange={(event) => setSource(event.target.value)} /></label>
        <label className="mt-4 block text-xs font-semibold text-muted">Memory<textarea className="mt-2 min-h-36 w-full rounded-2xl border border-black/10 bg-white/70 p-4 text-sm outline-none focus:border-accent" value={text} onChange={(event) => setText(event.target.value)} placeholder="A preference, rule, or verified fact…" /></label>
        <button className="button-primary mt-4 w-full" disabled={!text.trim()}>Save memory</button>
      </form>
      <section className="space-y-3">
        {items.length === 0 && <div className="panel p-8 text-sm text-muted">No structured memories yet.</div>}
        {items.map((item) => (
          <article key={item.id} className={`panel p-5 ${item.status === "inactive" ? "opacity-55" : ""}`}>
            <div className="flex items-start justify-between gap-4"><div><p className="eyebrow">{item.type} · {item.status}</p><p className="mt-3 leading-7">{item.text}</p></div><button className="min-h-11 rounded-2xl border border-black/10 px-4 text-xs font-semibold" onClick={() => void toggle(item)}>{item.status === "active" ? "Deactivate" : "Activate"}</button></div>
            <p className="mt-4 text-xs text-muted">Source: {item.source} · Confidence: {Math.round(item.confidence * 100)}%</p>
          </article>
        ))}
      </section>
    </div>
  );
}
