"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Archive, ChevronDown, Plus, Search } from "lucide-react";
import { apiJson } from "@/lib/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui-states";

type Memory = {
  id: string;
  type: string;
  text: string;
  source: string;
  confidence: number;
  status: "active" | "inactive";
  project_id?: string;
  updated_at: string;
};

const filters = ["all", "rule", "preference", "project", "fact"] as const;

export function MemoryManager() {
  const [items, setItems] = useState<Memory[]>([]);
  const [text, setText] = useState("");
  const [source, setSource] = useState("user");
  const [type, setType] = useState("fact");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof filters)[number]>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    try {
      const data = await apiJson<{ items: Memory[] }>("/api/memory");
      setItems(data.items);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const visibleItems = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return items.filter((item) => {
      const typeMatches = filter === "all" || item.type.toLowerCase() === filter || (filter === "project" && Boolean(item.project_id));
      const textMatches = !normalized || `${item.text} ${item.source} ${item.project_id || ""}`.toLowerCase().includes(normalized);
      return typeMatches && textMatches;
    });
  }, [filter, items, query]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    await apiJson("/api/memory", {
      method: "POST",
      body: JSON.stringify({ type, text: text.trim(), source, confidence: 1, project_id: "general" }),
    });
    setText("");
    await load();
  }

  async function toggle(item: Memory) {
    await apiJson(`/api/memory/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: item.status === "active" ? "inactive" : "active" }),
    });
    await load();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <label className="relative block w-full lg:max-w-md">
          <Search aria-hidden className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-text-tertiary" size={17} strokeWidth={1.7} />
          <input className="field w-full pl-10" type="search" aria-label="Search memory" placeholder="Search memory" value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <details className="group relative">
          <summary className="button-primary cursor-pointer list-none"><Plus aria-hidden size={17} />Add memory</summary>
          <form onSubmit={create} className="panel-elevated mt-2 p-4 lg:absolute lg:right-0 lg:z-20 lg:w-[420px]">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-medium">Add to long-term memory</h2>
              <ChevronDown aria-hidden className="transition-transform group-open:rotate-180" size={17} />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-xs font-medium text-text-secondary">Type
                <select className="field mt-1.5 w-full" value={type} onChange={(event) => setType(event.target.value)}>
                  <option value="fact">Fact</option><option value="rule">Rule</option><option value="preference">Preference</option><option value="project">Project</option>
                </select>
              </label>
              <label className="text-xs font-medium text-text-secondary">Source
                <input className="field mt-1.5 w-full" value={source} onChange={(event) => setSource(event.target.value)} />
              </label>
            </div>
            <label className="mt-3 block text-xs font-medium text-text-secondary">Memory
              <textarea className="textarea-field mt-1.5 min-h-32 w-full resize-y" value={text} onChange={(event) => setText(event.target.value)} placeholder="A preference, rule, or verified fact…" />
            </label>
            <button className="button-primary mt-3 w-full" disabled={!text.trim()}>Save memory</button>
          </form>
        </details>
      </div>

      <div className="scrollbar-subtle flex gap-2 overflow-x-auto pb-1" aria-label="Memory filters">
        {filters.map((item) => (
          <button key={item} type="button" className={`chip shrink-0 capitalize ${filter === item ? "bg-accent-soft text-accent-hover" : "hover:bg-surface"}`} onClick={() => setFilter(item)} aria-pressed={filter === item}>
            {item === "all" ? "All" : `${item.charAt(0).toUpperCase()}${item.slice(1)}s`}
          </button>
        ))}
      </div>

      {loading && <LoadingState label="Gathering your memories" />}
      {!loading && error && <ErrorState title="Memory is unavailable" detail="The memory service could not be reached. Refresh after the API is running." />}
      {!loading && !error && visibleItems.length === 0 && (
        <EmptyState title={items.length ? "No matching memories" : "Nothing saved yet"} description={items.length ? "Try another search or filter." : "Save a preference, rule, project note, or fact when you want it available later."} />
      )}
      {!loading && !error && visibleItems.length > 0 && (
        <section className="grid gap-3 md:grid-cols-2" aria-label="Saved memories">
          {visibleItems.map((item) => (
            <article key={item.id} className={`panel flex min-h-48 flex-col p-5 ${item.status === "inactive" ? "bg-surface/55" : ""}`}>
              <div className="flex items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  <span className="chip capitalize">{item.type}</span>
                  <span className={`chip ${item.status === "active" ? "bg-success/10 text-success" : ""}`}>{item.status === "active" ? "Active" : "Archived"}</span>
                </div>
                {item.status === "inactive" && <Archive aria-label="Archived" size={16} className="text-text-tertiary" />}
              </div>
              <p className="mt-5 flex-1 text-[15px] leading-7">{item.text}</p>
              <div className="mt-5 flex items-center justify-between gap-4 border-t border-line pt-4">
                <p className="truncate text-xs text-text-tertiary">{item.project_id || "General"} · {item.source}</p>
                <button className="button-quiet shrink-0 px-2 text-xs" onClick={() => void toggle(item)}>{item.status === "active" ? "Archive" : "Restore"}</button>
              </div>
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-text-tertiary">Details</summary>
                <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-small bg-surface-subtle p-3 font-mono text-[11px] text-text-secondary">
                  <dt>ID</dt><dd className="truncate">{item.id}</dd>
                  <dt>Confidence</dt><dd>{item.confidence}</dd>
                  <dt>Updated</dt><dd>{new Date(item.updated_at).toLocaleString()}</dd>
                </dl>
              </details>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
