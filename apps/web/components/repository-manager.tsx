"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiJson } from "@/lib/api";

type Artifact = { id: string; kind: string; title: string; locator: string; project_id?: string; created_at: string };
type TimelineEvent = { id: string; event_type: string; summary: string; project_id?: string; created_at: string; details: Record<string, unknown> };

export function RepositoryManager() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [title, setTitle] = useState("");
  const [locator, setLocator] = useState("");

  async function load() {
    const [artifactData, eventData] = await Promise.all([
      apiJson<{ items: Artifact[] }>("/api/repository/artifacts"),
      apiJson<{ items: TimelineEvent[] }>("/api/repository/timeline")
    ]);
    setArtifacts(artifactData.items); setEvents(eventData.items);
  }
  useEffect(() => { void load(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    await apiJson("/api/repository/artifacts", { method: "POST", body: JSON.stringify({ kind: "note", title, locator, project_id: "general", metadata: {} }) });
    setTitle(""); setLocator(""); await load();
  }

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <section className="panel p-5">
        <div className="flex items-end justify-between gap-4"><div><p className="eyebrow">Artifacts</p><h2 className="mt-2 text-2xl font-semibold">Files and records</h2></div><span className="text-sm text-muted">{artifacts.length}</span></div>
        <form onSubmit={create} className="mt-6 grid gap-3 rounded-3xl bg-black/[0.025] p-4"><input className="field" placeholder="Artifact title" value={title} onChange={(event) => setTitle(event.target.value)} /><input className="field" placeholder="Safe locator or note reference" value={locator} onChange={(event) => setLocator(event.target.value)} /><button className="button-primary" disabled={!title || !locator}>Add note artifact</button></form>
        <div className="mt-5 space-y-3">{artifacts.map((item) => <article key={item.id} className="rounded-2xl border border-black/5 bg-white/55 p-4"><p className="font-semibold">{item.title}</p><p className="mt-2 break-all text-xs text-muted">{item.kind} · {item.locator}</p></article>)}</div>
      </section>
      <section className="panel p-5"><p className="eyebrow">Timeline</p><h2 className="mt-2 text-2xl font-semibold">Recorded change</h2><div className="mt-6 space-y-5 border-l border-black/10 pl-5">{events.length === 0 && <p className="text-sm text-muted">Events appear when memory, tools, and artifacts change.</p>}{events.map((item) => <article key={item.id} className="relative"><span className="absolute -left-[25px] top-1 size-2 rounded-full bg-accent" /><p className="text-xs font-semibold uppercase tracking-wider text-muted">{item.event_type}</p><p className="mt-1 font-medium">{item.summary}</p><p className="mt-1 text-xs text-muted">{new Date(item.created_at).toLocaleString()}</p></article>)}</div></section>
    </div>
  );
}
