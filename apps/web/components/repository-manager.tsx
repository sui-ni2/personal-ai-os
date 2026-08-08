"use client";

import { FormEvent, useEffect, useState } from "react";
import { Clock3, FileText, FolderOpen, Plus } from "lucide-react";
import { apiJson } from "@/lib/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui-states";

type Artifact = { id: string; kind: string; title: string; locator: string; project_id?: string; created_at: string };
type TimelineEvent = { id: string; event_type: string; summary: string; project_id?: string; created_at: string; details: Record<string, unknown> };

export function RepositoryManager() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [title, setTitle] = useState("");
  const [locator, setLocator] = useState("");
  const [view, setView] = useState<"timeline" | "files">("timeline");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    try {
      const [artifactData, eventData] = await Promise.all([
        apiJson<{ items: Artifact[] }>("/api/repository/artifacts"),
        apiJson<{ items: TimelineEvent[] }>("/api/repository/timeline"),
      ]);
      setArtifacts(artifactData.items);
      setEvents(eventData.items);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    await apiJson("/api/repository/artifacts", {
      method: "POST",
      body: JSON.stringify({ kind: "note", title, locator, project_id: "general", metadata: {} }),
    });
    setTitle("");
    setLocator("");
    await load();
  }

  return (
    <div className="space-y-6">
      <div className="inline-flex rounded-control bg-surface-subtle p-1" role="tablist" aria-label="Repository view">
        <button type="button" role="tab" aria-selected={view === "timeline"} className={`min-h-10 rounded-small px-4 text-sm font-medium ${view === "timeline" ? "bg-surface-elevated shadow-soft" : "text-text-secondary"}`} onClick={() => setView("timeline")}>Timeline</button>
        <button type="button" role="tab" aria-selected={view === "files"} className={`min-h-10 rounded-small px-4 text-sm font-medium ${view === "files" ? "bg-surface-elevated shadow-soft" : "text-text-secondary"}`} onClick={() => setView("files")}>Files</button>
      </div>

      {loading && <LoadingState label="Reading repository activity" />}
      {!loading && error && <ErrorState title="Repository is unavailable" detail="Artifacts and timeline events could not be loaded. Refresh after the API is running." />}

      {!loading && !error && view === "timeline" && (
        <section aria-label="Repository timeline" className="max-w-3xl">
          <div className="mb-4 flex items-center gap-2">
            <Clock3 aria-hidden size={17} className="text-text-tertiary" strokeWidth={1.7} />
            <h2 className="text-sm font-medium uppercase tracking-[0.11em] text-text-tertiary">Activity</h2>
          </div>
          {events.length === 0 ? (
            <EmptyState title="No activity yet" description="Memory, tool, and artifact changes will appear here as they happen." />
          ) : (
            <ol className="relative space-y-1 before:absolute before:bottom-6 before:left-[19px] before:top-6 before:w-px before:bg-line sm:before:left-[77px]">
              {events.map((item) => (
                <li key={item.id} className="relative grid grid-cols-[40px_minmax(0,1fr)] gap-3 rounded-card px-1 py-4 sm:grid-cols-[78px_minmax(0,1fr)] sm:gap-5">
                  <time className="z-10 hidden bg-background pt-0.5 text-xs text-text-tertiary sm:block">{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
                  <span className="z-10 grid size-10 place-items-center rounded-control border border-line bg-surface text-text-secondary sm:absolute sm:left-[58px] sm:top-2.5">
                    <FileText aria-hidden size={17} strokeWidth={1.7} />
                  </span>
                  <article className="min-w-0 sm:pl-14">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-[15px] font-medium">{item.summary}</h3>
                      <span className="chip capitalize">{item.event_type.replaceAll("_", " ")}</span>
                    </div>
                    <p className="mt-1 text-sm text-text-secondary">{item.project_id || "General"}</p>
                    <time className="mt-1 block text-xs text-text-tertiary sm:hidden">{new Date(item.created_at).toLocaleString()}</time>
                  </article>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}

      {!loading && !error && view === "files" && (
        <section aria-label="Repository files" className="space-y-4">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="section-title">Files and records</h2>
              <p className="mt-1 text-sm text-text-secondary">{artifacts.length} saved {artifacts.length === 1 ? "item" : "items"}</p>
            </div>
            <details className="group relative">
              <summary className="button-primary cursor-pointer list-none"><Plus aria-hidden size={17} />Add note artifact</summary>
              <form onSubmit={create} className="panel-elevated mt-2 grid gap-3 p-4 sm:absolute sm:right-0 sm:z-20 sm:w-[420px]">
                <input className="field" aria-label="Artifact title" placeholder="Artifact title" value={title} onChange={(event) => setTitle(event.target.value)} />
                <input className="field font-mono text-xs" aria-label="Safe locator or note reference" placeholder="Safe locator or note reference" value={locator} onChange={(event) => setLocator(event.target.value)} />
                <button className="button-primary" disabled={!title || !locator}>Save artifact</button>
              </form>
            </details>
          </div>
          {artifacts.length === 0 ? (
            <EmptyState title="No files or records" description="Add a safe note reference when you want it tracked here." />
          ) : (
            <div className="overflow-hidden rounded-card border border-line bg-surface">
              {artifacts.map((item) => (
                <article key={item.id} className="flex min-h-16 items-center gap-3 border-b border-line px-4 py-3 last:border-b-0 sm:px-5">
                  <span className="grid size-9 shrink-0 place-items-center rounded-control bg-surface-subtle text-text-secondary"><FolderOpen aria-hidden size={17} strokeWidth={1.7} /></span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{item.title}</p>
                    <p className="mt-0.5 truncate font-mono text-[11px] text-text-tertiary">{item.locator}</p>
                  </div>
                  <span className="chip hidden capitalize sm:inline-flex">{item.kind}</span>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
