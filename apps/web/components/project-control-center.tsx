"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, FileText, ListChecks, Plus, RefreshCw } from "lucide-react";
import { apiJson } from "@/lib/api";
import { ErrorState, LoadingState } from "@/components/ui-states";

type Project = { id: string; name: string; description: string };
type StateRecord = { namespace: string; key: string; value: Record<string, unknown>; status: string; updated_at: string };
type ControlCenter = {
  project: Project;
  state: Record<string, StateRecord[]>;
  files: { id: string; title: string; locator: string }[];
  activity: { id: string; summary: string; created_at: string }[];
  reviewed_memory: { id: string; type: string; source: string }[];
  recovery: { status: string; message: string };
  recent_execution?: { status: string; retry_status: string; side_effect_status: string; updated_at: string };
  continuity: { conversation_count: number; state_record_count: number; provider_session_copied: boolean };
};

const labels: Record<string, string> = {
  goals: "Goal", current_state: "Current state", tasks: "Tasks", decisions: "Decisions", outcomes: "Outcomes",
  blockers: "Blockers", next_actions: "Next action", changed_files: "Changed files",
};

function summary(record: StateRecord) {
  return String(record.value.summary || record.value.title || record.value.text || record.key);
}

export function ProjectControlCenter({ projectId }: { projectId: string }) {
  const [data, setData] = useState<ControlCenter>();
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [kind, setKind] = useState("task");
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const sections = useMemo(() => Object.keys(labels), []);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      setData(await apiJson<ControlCenter>(`/api/projects/${encodeURIComponent(projectId)}/control-center`));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [projectId]);

  async function addRecord(event: FormEvent) {
    event.preventDefault();
    const value = text.trim();
    if (!value || saving) return;
    setSaving(true);
    try {
      const key = `${kind}-${Date.now()}`;
      await apiJson(`/api/projects/${encodeURIComponent(projectId)}/state/records`, {
        method: "PUT",
        body: JSON.stringify({ namespace: kind, key, value: { summary: value }, source: "user-control-center" }),
      });
      setText("");
      await load();
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState label="Loading project control center" />;
  if (error || !data) return <ErrorState title="Project control center is unavailable" detail="Your project data has not been changed. Refresh after the local API is running." />;

  const primaryGoal = data.state.goals?.[0];
  const primaryNext = data.state.next_actions?.[0];
  const blockers = data.state.blockers || [];

  return (
    <section className="panel scroll-mt-24 p-5 sm:p-7" aria-labelledby={`project-control-${projectId}`}>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <p className="eyebrow">Project control center</p>
          <h2 id={`project-control-${projectId}`} className="section-title mt-1">{data.project.name}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">{data.project.description}</p>
        </div>
        <button className="button-quiet" onClick={() => void load()}><RefreshCw aria-hidden size={15} />Refresh</button>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-control border border-line bg-surface/45 p-4"><p className="text-xs text-text-tertiary">Goal</p><p className="mt-1 text-sm font-medium">{primaryGoal ? summary(primaryGoal) : "Set a goal"}</p></article>
        <article className="rounded-control border border-line bg-surface/45 p-4"><p className="text-xs text-text-tertiary">Next action</p><p className="mt-1 text-sm font-medium">{primaryNext ? summary(primaryNext) : "Choose the next action"}</p></article>
        <article className="rounded-control border border-line bg-surface/45 p-4"><p className="text-xs text-text-tertiary">Blockers</p><p className="mt-1 text-sm font-medium">{blockers.length ? `${blockers.length} needs attention` : "None recorded"}</p></article>
        <article className="rounded-control border border-line bg-surface/45 p-4"><p className="text-xs text-text-tertiary">Last execution</p><p className="mt-1 text-sm font-medium">{data.recent_execution ? data.recent_execution.status.replaceAll("_", " ") : "No execution yet"}</p></article>
      </div>

      <form className="mt-5 grid gap-2 rounded-control border border-line bg-surface/35 p-3 sm:grid-cols-[10rem_1fr_auto]" onSubmit={addRecord}>
        <label><span className="sr-only">Record type</span><select className="field w-full" value={kind} onChange={(event) => setKind(event.target.value)}>{["goal", "current_state", "task", "decision", "outcome", "blocker", "next_action"].map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select></label>
        <label><span className="sr-only">Project update</span><input className="field w-full" value={text} onChange={(event) => setText(event.target.value)} placeholder="Add an authoritative project update" maxLength={500} required /></label>
        <button className="button-secondary min-h-10" disabled={saving}><Plus aria-hidden size={15} />{saving ? "Saving…" : "Add"}</button>
      </form>

      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        {sections.map((section) => {
          const records = data.state[section] || [];
          if (!records.length && !["tasks", "blockers", "next_actions"].includes(section)) return null;
          return <article key={section} className="rounded-control border border-line bg-surface/25 p-4"><div className="flex items-center gap-2"><ListChecks aria-hidden size={16} className="text-accent" /><h3 className="text-sm font-medium">{labels[section]}</h3><span className="ml-auto text-xs text-text-tertiary">{records.length}</span></div>{records.length ? <ul className="mt-3 space-y-2 text-sm text-text-secondary">{records.slice(0, 4).map((record) => <li key={`${record.namespace}-${record.key}`} className="flex gap-2"><CheckCircle2 aria-hidden size={15} className="mt-0.5 shrink-0 text-success" /><span>{summary(record)}</span></li>)}</ul> : <p className="mt-3 text-sm text-text-tertiary">Nothing recorded.</p>}</article>;
        })}
        <article className="rounded-control border border-line bg-surface/25 p-4"><div className="flex items-center gap-2"><FileText aria-hidden size={16} className="text-accent" /><h3 className="text-sm font-medium">Files and reviewed memory</h3></div><p className="mt-3 text-sm text-text-secondary">{data.files.length} file references · {data.reviewed_memory.length} reviewed memories</p><p className="mt-2 text-xs leading-5 text-text-tertiary">Provider session state is never copied into project continuity.</p></article>
        <article className="rounded-control border border-line bg-surface/25 p-4"><div className="flex items-center gap-2"><AlertTriangle aria-hidden size={16} className={data.recovery.status === "clean" ? "text-success" : "text-warning"} /><h3 className="text-sm font-medium">Recovery</h3></div><p className="mt-3 text-sm text-text-secondary">{data.recovery.message}</p></article>
      </div>

      <details className="mt-5 rounded-control border border-line bg-surface/20 p-4"><summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-medium"><ChevronDown aria-hidden size={16} />Advanced continuity details</summary><div className="mt-3 grid gap-2 text-xs text-text-secondary sm:grid-cols-3"><p>{data.continuity.conversation_count} conversations</p><p>{data.continuity.state_record_count} state records</p><p>{data.activity.length} recent activity receipts</p></div></details>
    </section>
  );
}
