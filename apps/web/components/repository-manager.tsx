"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ChevronDown, Clock3, FileText, FolderOpen, Plus } from "lucide-react";
import { apiJson } from "@/lib/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui-states";

type Artifact = { id: string; kind: string; title: string; locator: string; project_id?: string; created_at: string };
type TimelineEvent = { id: string; event_type: string; summary: string; artifact_id?: string; project_id?: string; created_at: string; details: Record<string, unknown> };

function dayKey(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value);
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

function dayLabel(value: string) {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (dayKey(date) === dayKey(today)) return "Today";
  if (dayKey(date) === dayKey(yesterday)) return "Yesterday";
  return date.toLocaleDateString([], { month: "long", day: "numeric", year: date.getFullYear() === today.getFullYear() ? undefined : "numeric" });
}

function eventDetails(item: TimelineEvent, artifact?: Artifact) {
  const details: { label: string; value: string; mono?: boolean }[] = [];
  if (artifact) {
    details.push({ label: "Artifact", value: artifact.title });
    details.push({ label: "Location", value: artifact.locator, mono: true });
  }
  for (const [key, value] of Object.entries(item.details)) {
    if (details.length >= 5 || /(^id$|_id$|key|token|secret|cookie|trace|stack|reasoning|thought)/i.test(key)) continue;
    if (typeof value !== "string" && typeof value !== "number" && typeof value !== "boolean") continue;
    details.push({ label: key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()), value: String(value) });
  }
  return details;
}

export function RepositoryManager() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [title, setTitle] = useState("");
  const [locator, setLocator] = useState("");
  const [view, setView] = useState<"timeline" | "files">("timeline");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const artifactById = useMemo(() => new Map(artifacts.map((item) => [item.id, item])), [artifacts]);
  const groupedEvents = useMemo(() => {
    const groups: { key: string; label: string; items: TimelineEvent[] }[] = [];
    for (const item of events) {
      const key = dayKey(item.created_at);
      const existing = groups.find((group) => group.key === key);
      if (existing) existing.items.push(item);
      else groups.push({ key, label: dayLabel(item.created_at), items: [item] });
    }
    return groups;
  }, [events]);

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
            <h2 className="text-sm font-medium text-text-secondary">What your AI has done</h2>
          </div>
          {events.length === 0 ? (
            <EmptyState title="No activity yet" description="Memory, tool, and artifact changes will appear here as they happen." />
          ) : (
            <div className="space-y-8">
              {groupedEvents.map((group) => (
                <section key={group.key} aria-labelledby={`repository-day-${group.key}`}>
                  <h3 id={`repository-day-${group.key}`} className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-text-tertiary">{group.label}</h3>
                  <ol className="overflow-hidden rounded-card border border-line bg-surface">
                    {group.items.map((item) => {
                      const artifact = item.artifact_id ? artifactById.get(item.artifact_id) : undefined;
                      const details = eventDetails(item, artifact);
                      return (
                        <li key={item.id} className="border-b border-line last:border-b-0">
                          <details className="group/event">
                            <summary className="cursor-pointer list-none px-4 py-4 sm:px-5">
                              <span className="grid grid-cols-[52px_minmax(0,1fr)_20px] gap-3 sm:grid-cols-[64px_minmax(0,1fr)_20px]">
                                <time className="pt-0.5 text-xs font-medium tabular-nums text-text-tertiary">{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
                                <span className="min-w-0">
                                  <span className="flex items-start gap-3">
                                    <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-control bg-surface-subtle text-text-secondary"><FileText aria-hidden size={16} strokeWidth={1.7} /></span>
                                    <span className="min-w-0 flex-1">
                                      <span className="block text-[15px] font-medium leading-6">{item.summary}</span>
                                      <span className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-text-tertiary">
                                        <span>{item.project_id || "General"}</span>
                                        <span aria-hidden>·</span>
                                        <span className="capitalize">{item.event_type.replaceAll("_", " ").replaceAll(".", " ")}</span>
                                        <span aria-hidden>·</span>
                                        <span className="text-success">Recorded</span>
                                      </span>
                                      {artifact && <span className="mt-2 block truncate font-mono text-[11px] text-text-secondary">{artifact.locator}</span>}
                                    </span>
                                  </span>
                                </span>
                                <ChevronDown aria-hidden size={17} className="mt-1 text-text-tertiary transition-transform duration-150 group-open/event:rotate-180" />
                              </span>
                            </summary>
                            <div className="border-t border-line bg-surface-subtle/45 px-4 py-4 sm:pl-[100px] sm:pr-5">
                              {details.length ? <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-xs">{details.map((detail) => <div key={`${detail.label}-${detail.value}`} className="contents"><dt className="font-medium text-text-tertiary">{detail.label}</dt><dd className={`min-w-0 break-words text-text-secondary ${detail.mono ? "font-mono text-[11px]" : ""}`}>{detail.value}</dd></div>)}</dl> : <p className="text-xs leading-5 text-text-secondary">No additional details were recorded for this event.</p>}
                            </div>
                          </details>
                        </li>
                      );
                    })}
                  </ol>
                </section>
              ))}
            </div>
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
