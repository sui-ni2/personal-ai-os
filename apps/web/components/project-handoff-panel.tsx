"use client";

import { useState } from "react";
import { Check, ClipboardCopy, RefreshCw, ShieldCheck, X } from "lucide-react";
import { apiJson } from "@/lib/api";

type HandoffMode = "compact" | "full";
type HandoffSnapshot = {
  project_id: string;
  mode: HandoffMode;
  counts: { states: number; experiences: number; workflows: number };
  truncated: boolean;
  states: unknown[];
  experiences: unknown[];
  workflows: unknown[];
};

type Props = {
  projectId: string;
  projectName: string;
};

export function ProjectHandoffPanel({ projectId, projectName }: Props) {
  const [snapshot, setSnapshot] = useState<HandoffSnapshot | null>(null);
  const [loadingMode, setLoadingMode] = useState<HandoffMode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function load(mode: HandoffMode) {
    setLoadingMode(mode);
    setError(null);
    setCopied(false);
    try {
      const data = await apiJson<HandoffSnapshot>(
        `/api/projects/${encodeURIComponent(projectId)}/handoff?mode=${mode}`,
      );
      setSnapshot(data);
    } catch {
      setError("Continuity snapshot could not be loaded. Confirm the API is running, then try again.");
    } finally {
      setLoadingMode(null);
    }
  }

  async function copySnapshot() {
    if (!snapshot) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(snapshot, null, 2));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("The snapshot is visible below, but this browser did not allow clipboard access.");
    }
  }

  if (!snapshot) {
    return (
      <div className="mt-4 border-t border-line pt-4">
        <button
          type="button"
          className="button-quiet px-2 text-accent-hover"
          disabled={loadingMode !== null}
          onClick={() => void load("compact")}
        >
          <ShieldCheck aria-hidden size={15} />
          {loadingMode === "compact" ? "Loading continuity…" : "Continuity"}
        </button>
        {error ? <p className="mt-2 text-xs leading-5 text-danger">{error}</p> : null}
      </div>
    );
  }

  return (
    <section className="mt-4 rounded-card border border-line bg-surface/70 p-4" aria-label={`${projectName} continuity handoff`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Continuity snapshot</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h4 className="font-medium text-text-primary">{projectName}</h4>
            <span className="chip capitalize">{snapshot.mode}</span>
            {snapshot.truncated ? <span className="chip">Bounded</span> : null}
          </div>
        </div>
        <button
          type="button"
          className="button-quiet px-2"
          aria-label="Close continuity preview"
          onClick={() => {
            setSnapshot(null);
            setError(null);
            setCopied(false);
          }}
        >
          <X aria-hidden size={15} />
        </button>
      </div>

      <p className="mt-3 text-xs leading-5 text-text-secondary">
        {snapshot.counts.states} state · {snapshot.counts.experiences} experience · {snapshot.counts.workflows} workflow
        {snapshot.counts.workflows === 1 ? "" : "s"}. This preview is read-only and comes from persisted project continuity state.
      </p>
      {snapshot.truncated ? (
        <p className="mt-2 text-xs leading-5 text-warning">
          Older records are outside this bounded snapshot. Total counts above still reflect the stored project state.
        </p>
      ) : null}
      {snapshot.mode === "compact" ? (
        <p className="mt-2 text-xs leading-5 text-text-tertiary">
          Compact omits source metadata and workflow definitions. Full details remain bounded and require an explicit choice.
        </p>
      ) : (
        <p className="mt-2 text-xs leading-5 text-text-tertiary">
          Full includes richer current-record metadata, but still excludes state history, transition receipts, provider sessions, and credentials.
        </p>
      )}

      <pre className="mt-3 max-h-64 overflow-auto rounded-control border border-line bg-surface-subtle p-3 text-[11px] leading-5 text-text-secondary">
        {JSON.stringify(snapshot, null, 2)}
      </pre>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="button-quiet px-3"
          disabled={loadingMode !== null}
          onClick={() => void load("compact")}
        >
          <RefreshCw aria-hidden size={14} />
          {loadingMode === "compact" ? "Refreshing…" : "Refresh compact"}
        </button>
        {snapshot.mode === "compact" ? (
          <button
            type="button"
            className="button-quiet px-3"
            disabled={loadingMode !== null}
            onClick={() => void load("full")}
          >
            <ShieldCheck aria-hidden size={14} />
            {loadingMode === "full" ? "Loading full…" : "Load full details"}
          </button>
        ) : null}
        <button type="button" className="button-quiet px-3" onClick={() => void copySnapshot()}>
          {copied ? <Check aria-hidden size={14} /> : <ClipboardCopy aria-hidden size={14} />}
          {copied ? "Copied" : "Copy snapshot"}
        </button>
      </div>
      {error ? <p className="mt-2 text-xs leading-5 text-danger">{error}</p> : null}
    </section>
  );
}
