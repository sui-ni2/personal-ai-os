"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Activity, CalendarDays, Database, Search, ShieldCheck } from "lucide-react";
import { apiJson } from "@/lib/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui-states";

type View = "home" | "history" | "candidates" | "audit";
type Candidate = {
  number: string;
  generated_order: number;
  raw_score: number;
  adjusted_score: number;
  feature_scores: Record<string, number>;
  filters_triggered: string[];
  elimination_reason?: string;
  survived_final_filter: boolean;
  final_rank: number;
  is_top10: boolean;
  is_top5: boolean;
  model_version: string;
  created_at: string;
};
type Home = {
  schedule: string;
  execution_path: string;
  paper_only: boolean;
  latest_issue?: { issue: string; status: string; candidate_count: number; retry_at?: string };
  top10: Candidate[];
  review_count: number;
};
type HistoryItem = {
  issue: string;
  draw_date?: string;
  status: string;
  official_result?: string;
  candidate_count: number;
  metrics?: { generated: boolean; final_rank?: number; hit_top10: boolean; hit_top5: boolean };
};
type Audit = {
  model_version: string;
  workflow_version: string;
  execution_path: string;
  paper_only: boolean;
  rules: Array<{ rule_id: string; label: string; weight: number; positive_count: number; negative_count: number; active: boolean }>;
  events: Array<{ id: number; issue?: string; action: string; payload: Record<string, unknown>; created_at: string }>;
};

const navigation = [
  ["home", "Home", "/projects/p5"],
  ["history", "History", "/projects/p5/history"],
  ["candidates", "Candidate Explorer", "/projects/p5/candidates"],
  ["audit", "Model Audit", "/projects/p5/audit"],
] as const;

function P5Header({ view }: { view: View }) {
  return (
    <>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">Projects / P5</p>
          <h1 className="page-title mt-1">排列5 · 10xthink</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">复盘先行、恰好 10,000 组全量留痕、Top10 与 Top5 锁定。独立于 P3 和通用核心。</p>
        </div>
        <span className="chip w-fit"><span className="status-dot bg-success" />GPT / ChatGPT · 纸面研究</span>
      </div>
      <nav className="scrollbar-subtle mt-6 flex gap-2 overflow-x-auto pb-1" aria-label="P5 sections">
        {navigation.map(([id, label, href]) => (
          <Link key={id} href={href} aria-current={id === view ? "page" : undefined} className={`whitespace-nowrap rounded-control px-3.5 py-2 text-sm font-medium ${id === view ? "bg-accent-soft text-accent-hover" : "text-text-secondary hover:bg-surface-subtle"}`}>
            {label}
          </Link>
        ))}
      </nav>
    </>
  );
}

function HomeView() {
  const [data, setData] = useState<Home>();
  const [error, setError] = useState(false);
  useEffect(() => { void apiJson<Home>("/api/projects/p5/home").then(setData).catch(() => setError(true)); }, []);
  if (error) return <ErrorState title="P5 status is unavailable" detail="Start the API and try again." />;
  if (!data) return <LoadingState label="Opening P5" />;
  return (
    <div className="mt-6 space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <article className="panel p-5"><CalendarDays className="text-accent" size={19} /><p className="mt-4 text-xs text-text-tertiary">Current state</p><p className="mt-1 text-lg font-medium">{data.latest_issue?.status || "No run yet"}</p><p className="mt-1 text-sm text-text-secondary">{data.latest_issue ? `Issue ${data.latest_issue.issue}` : "Waiting for the first confirmed result"}</p></article>
        <article className="panel p-5"><Database className="text-accent" size={19} /><p className="mt-4 text-xs text-text-tertiary">Persisted candidates</p><p className="mt-1 text-lg font-medium">{(data.latest_issue?.candidate_count || 0).toLocaleString()}</p><p className="mt-1 text-sm text-text-secondary">Exactly 10,000 when an issue is locked</p></article>
        <article className="panel p-5"><ShieldCheck className="text-accent" size={19} /><p className="mt-4 text-xs text-text-tertiary">Completed reviews</p><p className="mt-1 text-lg font-medium">{data.review_count}</p><p className="mt-1 text-sm text-text-secondary">No single draw retunes a rule</p></article>
      </div>
      <article className="panel p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4"><div><p className="eyebrow">Latest lock</p><h2 className="section-title mt-1">Top10 / Top5</h2></div><span className="chip">22:22 Asia/Shanghai</span></div>
        {data.top10.length ? <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">{data.top10.map((candidate) => <div key={candidate.number} className={`rounded-control border p-3 ${candidate.is_top5 ? "border-accent bg-accent-soft/45" : "border-line bg-surface-subtle/45"}`}><span className="text-xs text-text-tertiary">#{candidate.final_rank}</span><p className="mt-1 font-mono text-lg tracking-[0.12em]">{candidate.number}</p><span className="text-xs text-text-secondary">{candidate.adjusted_score.toFixed(4)}</span></div>)}</div> : <div className="mt-5"><EmptyState title="No locked issue" description="After 22:22, the workflow waits for a confirmed official result before generating the next issue." /></div>}
        <p className="mt-5 text-xs leading-5 text-text-tertiary">{data.schedule}. Locked prefixes are research artifacts, not betting authorization.</p>
      </article>
    </div>
  );
}

function HistoryView() {
  const [items, setItems] = useState<HistoryItem[]>();
  const [error, setError] = useState(false);
  useEffect(() => { void apiJson<{ items: HistoryItem[] }>("/api/projects/p5/history").then((data) => setItems(data.items)).catch(() => setError(true)); }, []);
  if (error) return <ErrorState title="History is unavailable" detail="The P5 history endpoint could not be reached." />;
  if (!items) return <LoadingState label="Loading P5 history" />;
  if (!items.length) return <div className="mt-6"><EmptyState title="No P5 history yet" description="Confirmed daily runs and wait states will appear here." /></div>;
  return <div className="panel mt-6 overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-surface-subtle text-xs text-text-tertiary"><tr><th className="px-5 py-3 font-medium">Issue</th><th className="px-5 py-3 font-medium">Status</th><th className="px-5 py-3 font-medium">Result</th><th className="px-5 py-3 font-medium">Candidates</th><th className="px-5 py-3 font-medium">Review</th></tr></thead><tbody>{items.map((item) => <tr key={item.issue} className="border-t border-line"><td className="px-5 py-4 font-medium">{item.issue}<span className="block text-xs font-normal text-text-tertiary">{item.draw_date || "—"}</span></td><td className="px-5 py-4"><span className="chip">{item.status}</span></td><td className="px-5 py-4 font-mono">{item.official_result || "—"}</td><td className="px-5 py-4">{item.candidate_count.toLocaleString()}</td><td className="px-5 py-4 text-text-secondary">{item.metrics ? item.metrics.generated ? `Generated · rank ${item.metrics.final_rank}` : "Not generated" : "Pending"}</td></tr>)}</tbody></table></div></div>;
}

function CandidateView() {
  const [issue, setIssue] = useState("");
  const [number, setNumber] = useState("");
  const [result, setResult] = useState<{ generated: boolean; candidate?: Candidate }>();
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setResult(undefined);
    try { setResult(await apiJson(`/api/projects/p5/candidates?issue=${encodeURIComponent(issue)}&number=${encodeURIComponent(number)}`)); }
    catch { setError("No matching locked issue could be queried."); }
  }
  return <div className="mt-6 grid gap-4 lg:grid-cols-[360px_1fr]"><form onSubmit={submit} className="panel h-fit p-5"><Search className="text-accent" size={20} /><h2 className="section-title mt-4">Find any number</h2><p className="mt-2 text-sm leading-6 text-text-secondary">Enter an issue and five-digit number to see whether it was generated, scored, filtered, and ranked.</p><label className="mt-5 block text-xs font-medium text-text-secondary">Issue<input className="field mt-1.5 w-full" required pattern="[0-9]{5,12}" value={issue} onChange={(event) => setIssue(event.target.value)} placeholder="26211" /></label><label className="mt-4 block text-xs font-medium text-text-secondary">Number<input className="field mt-1.5 w-full font-mono" required pattern="[0-9]{5}" value={number} onChange={(event) => setNumber(event.target.value)} placeholder="01234" /></label><button className="button-primary mt-5 w-full" type="submit">Query candidate</button></form><section className="panel min-h-[360px] p-5 sm:p-6">{error ? <ErrorState title="Query failed" detail={error} /> : !result ? <EmptyState title="Candidate audit is ready" description="A lookup returns the generation flag plus every persisted score, filter, elimination reason, and final rank." /> : !result.generated || !result.candidate ? <EmptyState title="Not generated" description="This number is not part of the issue's immutable 10,000-candidate lock." /> : <CandidateDetail item={result.candidate} />}</section></div>;
}

function CandidateDetail({ item }: { item: Candidate }) {
  return <div><div className="flex items-start justify-between gap-4"><div><p className="eyebrow">Generated candidate</p><h2 className="mt-1 font-mono text-3xl tracking-[0.14em]">{item.number}</h2></div><span className="chip">Rank #{item.final_rank}</span></div><div className="mt-6 grid gap-3 sm:grid-cols-3"><div className="rounded-control bg-surface-subtle p-4"><span className="text-xs text-text-tertiary">Generated order</span><p className="mt-1 text-lg font-medium">{item.generated_order}</p></div><div className="rounded-control bg-surface-subtle p-4"><span className="text-xs text-text-tertiary">Raw score</span><p className="mt-1 text-lg font-medium">{item.raw_score.toFixed(6)}</p></div><div className="rounded-control bg-surface-subtle p-4"><span className="text-xs text-text-tertiary">Adjusted</span><p className="mt-1 text-lg font-medium">{item.adjusted_score.toFixed(6)}</p></div></div><dl className="mt-6 space-y-3 text-sm"><div className="flex justify-between gap-4 border-b border-line pb-3"><dt className="text-text-secondary">Final filter</dt><dd>{item.survived_final_filter ? "Survived" : item.elimination_reason}</dd></div><div className="flex justify-between gap-4 border-b border-line pb-3"><dt className="text-text-secondary">Prefixes</dt><dd>{item.is_top5 ? "Top5 + Top10" : item.is_top10 ? "Top10" : "None"}</dd></div><div className="flex justify-between gap-4 border-b border-line pb-3"><dt className="text-text-secondary">Triggered filters</dt><dd className="text-right">{item.filters_triggered.join(", ") || "None"}</dd></div><div className="flex justify-between gap-4"><dt className="text-text-secondary">Model</dt><dd className="font-mono text-xs">{item.model_version}</dd></div></dl></div>;
}

function AuditView() {
  const [data, setData] = useState<Audit>();
  const [error, setError] = useState(false);
  useEffect(() => { void apiJson<Audit>("/api/projects/p5/audit").then(setData).catch(() => setError(true)); }, []);
  if (error) return <ErrorState title="Audit is unavailable" detail="The P5 audit endpoint could not be reached." />;
  if (!data) return <LoadingState label="Loading model audit" />;
  return <div className="mt-6 space-y-4"><div className="grid gap-4 sm:grid-cols-2"><article className="panel p-5"><Activity className="text-accent" size={19} /><p className="mt-4 text-xs text-text-tertiary">Model version</p><p className="mt-1 font-mono text-sm">{data.model_version}</p><p className="mt-3 text-xs text-text-secondary">{data.workflow_version}</p></article><article className="panel p-5"><ShieldCheck className="text-accent" size={19} /><p className="mt-4 text-xs text-text-tertiary">Execution boundary</p><p className="mt-1 text-lg font-medium">{data.execution_path}</p><p className="mt-1 text-xs text-text-secondary">P5-only · paper-only · no Codex</p></article></div><section className="panel p-5 sm:p-6"><p className="eyebrow">Cumulative rule evidence</p><h2 className="section-title mt-1">Active scoring rules</h2><div className="mt-5 space-y-3">{data.rules.map((rule) => <div key={rule.rule_id} className="rounded-control bg-surface-subtle/55 p-4"><div className="flex items-center justify-between gap-4"><span className="font-medium">{rule.label}</span><span className="font-mono text-sm">{rule.weight.toFixed(4)}</span></div><p className="mt-2 text-xs text-text-secondary">Positive {rule.positive_count} · Negative {rule.negative_count} · {rule.active ? "Active" : "Paused"}</p></div>)}</div></section><section className="panel p-5 sm:p-6"><p className="eyebrow">Append-only audit</p><h2 className="section-title mt-1">Recent workflow events</h2>{data.events.length ? <div className="mt-5 space-y-3">{data.events.map((event) => <div key={event.id} className="flex gap-3 border-b border-line pb-3 last:border-0"><span className="status-dot mt-2 bg-accent" /><div><p className="text-sm font-medium">{event.action}</p><p className="mt-1 text-xs text-text-tertiary">Issue {event.issue || "—"} · {new Date(event.created_at).toLocaleString()}</p></div></div>)}</div> : <div className="mt-5"><EmptyState title="No audit events yet" description="Wait, review, and lock events will be appended here." /></div>}</section></div>;
}

export function P5Workspace({ view }: { view: View }) {
  return <div className="page-frame"><P5Header view={view} />{view === "home" ? <HomeView /> : view === "history" ? <HistoryView /> : view === "candidates" ? <CandidateView /> : <AuditView />}</div>;
}
