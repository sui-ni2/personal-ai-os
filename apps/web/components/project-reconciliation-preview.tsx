"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, RefreshCw, ShieldCheck, X } from "lucide-react";
import { apiJson } from "@/lib/api";

type EvidenceLabel =
  | "RECORDED"
  | "WORKFLOW_POSITION"
  | "NEEDS_CONFIRMATION"
  | "CONFLICT"
  | "INSUFFICIENT_EVIDENCE";

type EvidenceRecord = {
  evidence_label: EvidenceLabel;
  reason_code: string;
  review_required: boolean;
};

type StateRecord = EvidenceRecord & {
  namespace: string;
  key: string;
  version: number;
  storage_status: string;
  history_integrity: string;
  history_versions_expected: number;
  history_versions_observed: number;
};

type WorkflowRecord = EvidenceRecord & {
  workflow_id: string;
  run_key: string;
  version: number;
  recorded_status: string;
  next_step: string | null;
  transition_history_integrity: string;
  external_execution: "UNVERIFIED";
};

type ExecutionRecord = EvidenceRecord & {
  execution_id: string;
  status: string;
  retry_status: string;
  side_effect_status: string;
  created_at: string;
  updated_at: string;
};

type ReconciliationPreview = {
  project_id: string;
  read_at: string;
  state_fingerprint: string;
  evidence_scope: "PERSISTED_METADATA_ONLY";
  counts: { states: number; workflows: number; executions: number };
  summary: { by_label: Record<EvidenceLabel, number> };
  needs_user_review: boolean;
  truncated: boolean;
  coverage: {
    states: "complete" | "partial";
    workflows: "complete" | "partial";
    executions: "complete" | "partial";
    evidence_label: "COMPLETE" | "INSUFFICIENT_EVIDENCE";
  };
  state_records: StateRecord[];
  workflow_records: WorkflowRecord[];
  execution_records: ExecutionRecord[];
};

const labelMeta: Record<EvidenceLabel, { title: string; className: string }> = {
  RECORDED: { title: "Recorded", className: "text-text-secondary" },
  WORKFLOW_POSITION: { title: "Workflow position", className: "text-accent-hover" },
  NEEDS_CONFIRMATION: { title: "Needs confirmation", className: "text-warning" },
  CONFLICT: { title: "Conflict", className: "text-danger" },
  INSUFFICIENT_EVIDENCE: { title: "Insufficient evidence", className: "text-warning" },
};

const reasonText: Record<string, string> = {
  STORED_NOT_EXECUTION_PROOF: "A versioned record exists; it does not prove that the underlying work happened.",
  LOCKED_STATE_REQUIRES_EXPLICIT_SUPERSESSION: "This record is locked. Changing it requires an explicit supersession action.",
  STATE_MARKED_SUPERSEDED: "The stored record is marked as superseded.",
  STATE_HISTORY_GAP: "One or more expected prior versions are missing from the stored history.",
  STATE_HISTORY_VERSION_CONFLICT: "Stored history versions disagree with the current record version.",
  INVALID_STATE_VERSION: "The stored state version is invalid.",
  UNKNOWN_STATE_STATUS: "The stored state status is not recognized.",
  WORKFLOW_STATE_NOT_EXTERNAL_RECEIPT: "The workflow position is recorded; external execution remains unverified.",
  WORKFLOW_DEFINITION_UNREADABLE: "The stored workflow definition cannot be safely interpreted.",
  WORKFLOW_POSITION_OUT_OF_RANGE: "The stored workflow cursor is outside its defined steps.",
  WORKFLOW_VERSION_CURSOR_MISMATCH: "The workflow version and recorded cursor disagree.",
  UNKNOWN_WORKFLOW_STATUS: "The stored workflow status is not recognized.",
  WORKFLOW_STATUS_CURSOR_MISMATCH: "The workflow status and terminal position disagree.",
  WORKFLOW_TRANSITION_VERSION_CONFLICT: "Stored transition versions disagree with the workflow version.",
  WORKFLOW_TRANSITION_HISTORY_GAP: "One or more expected workflow transitions are missing.",
  EXTERNAL_SIDE_EFFECT_OUTCOME_UNKNOWN: "The external action may have started, but its final outcome is unknown. Confirm before retrying.",
  EXTERNAL_SIDE_EFFECT_STILL_STARTED: "The external action is recorded as started and needs confirmation before proceeding.",
  RETRY_REQUIRES_EXPLICIT_CONFIRMATION: "The recorded execution requires explicit confirmation before retrying.",
  EXECUTION_RESULT_RECORDED_NOT_INDEPENDENT_PROOF: "A successful tool response was recorded; this is not independent proof of the external result.",
  UNKNOWN_EXTERNAL_EXECUTION_STATUS: "The external execution status is not recognized.",
};

function EvidenceTag({ label }: { label: EvidenceLabel }) {
  const meta = labelMeta[label];
  return <span className={`chip min-h-8 px-2.5 ${meta.className}`}>{meta.title}</span>;
}

function formatTime(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function ProjectReconciliationPreview({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<ReconciliationPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limit, setLimit] = useState(20);
  const controller = useRef<AbortController | null>(null);
  const panelId = `project-reconciliation-${projectId}`;

  useEffect(() => () => controller.current?.abort(), []);

  async function load(nextLimit = limit) {
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    setOpen(true);
    setLoading(true);
    setError(null);
    setPreview(null);
    setLimit(nextLimit);
    try {
      const result = await apiJson<ReconciliationPreview>(
        `/api/projects/${encodeURIComponent(projectId)}/control-center/reconciliation-preview?limit=${nextLimit}`,
        { signal: nextController.signal },
      );
      if (controller.current === nextController) setPreview(result);
    } catch {
      if (!nextController.signal.aborted) {
        setError("The read-only review could not be loaded. Project data was not changed. Try again.");
      }
    } finally {
      if (controller.current === nextController) setLoading(false);
    }
  }

  function close() {
    controller.current?.abort();
    controller.current = null;
    setOpen(false);
    setPreview(null);
    setError(null);
    setLoading(false);
  }

  return (
    <div className="mt-5 border-t border-line pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-text-primary">Project state review</p>
          <p className="mt-1 text-xs leading-5 text-text-tertiary">
            An on-demand, read-only check of stored versions and unresolved execution records.
          </p>
        </div>
        <button
          type="button"
          className="button-quiet px-3 text-accent-hover"
          aria-expanded={open}
          aria-controls={open ? panelId : undefined}
          onClick={() => open ? void load() : void load(20)}
          disabled={loading}
        >
          <ShieldCheck aria-hidden size={15} />
          {loading ? "Reviewing…" : open ? "Refresh review" : "Review recorded state"}
        </button>
      </div>

      {open ? (
        <section
          id={panelId}
          className="mt-4 rounded-card border border-line bg-surface/45 p-4 sm:p-5"
          aria-labelledby={`${panelId}-title`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="eyebrow">Read-only snapshot</p>
              <h3 id={`${panelId}-title`} className="mt-1 text-base font-medium text-text-primary">Evidence review</h3>
            </div>
            <button type="button" className="icon-button size-9" aria-label="Close state review" onClick={close}>
              <X aria-hidden size={16} />
            </button>
          </div>

          {loading ? <p className="mt-4 text-sm text-text-secondary" role="status">Reading bounded project metadata…</p> : null}
          {error ? (
            <div className="mt-4 space-y-3" role="alert">
              <p className="text-sm text-danger">{error}</p>
              <button type="button" className="button-secondary min-h-9" onClick={() => void load()}>
                <RefreshCw aria-hidden size={14} />Try again
              </button>
            </div>
          ) : null}

          {preview ? (
            <>
              <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
                {(Object.keys(labelMeta) as EvidenceLabel[]).map((label) => (
                  <article key={label} className="rounded-control border border-line bg-surface p-3">
                    <p className="text-xs text-text-tertiary">{labelMeta[label].title}</p>
                    <p className="mt-1 text-xl font-medium tabular-nums text-text-primary">{preview.summary.by_label[label] ?? 0}</p>
                  </article>
                ))}
              </div>

              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-tertiary">
                <span>{preview.counts.states} state records</span>
                <span>{preview.counts.workflows} workflows</span>
                <span>{preview.counts.executions} external execution records</span>
                <span>Checked {formatTime(preview.read_at)}</span>
              </div>

              {preview.needs_user_review ? (
                <div className="mt-4 flex items-start gap-2 rounded-control border border-warning bg-surface p-3" role="status">
                  <AlertTriangle aria-hidden size={16} className="mt-0.5 shrink-0 text-warning" />
                  <p className="text-sm leading-5 text-text-secondary">
                    Review needed. At least one record is inconsistent, incomplete, locked, requires confirmation, or the snapshot is partial. This preview does not resolve or change it.
                  </p>
                </div>
              ) : (
                <p className="mt-4 rounded-control border border-line bg-surface p-3 text-sm leading-5 text-text-secondary">
                  No review flags were found in the displayed records. This is not proof that no external action occurred.
                </p>
              )}

              {preview.truncated ? (
                <div className="mt-3 rounded-control border border-warning bg-surface p-3">
                  <p className="text-sm font-medium text-warning">Partial view — older records are outside this snapshot.</p>
                  <p className="mt-1 text-xs leading-5 text-text-secondary">
                    Counts above reflect the full stored totals. The current limit is {limit}; the preview can show up to 100 records per category.
                  </p>
                  {limit < 100 ? (
                    <button type="button" className="button-quiet mt-2 min-h-9 px-2 text-accent-hover" disabled={loading} onClick={() => void load(100)}>
                      Show up to 100 records
                    </button>
                  ) : null}
                </div>
              ) : null}

              <div className="mt-5 space-y-4">
                <section aria-labelledby={`${panelId}-states`}>
                  <div className="flex items-center justify-between gap-3">
                    <h4 id={`${panelId}-states`} className="text-sm font-medium text-text-primary">Stored project state</h4>
                    <span className="text-xs text-text-tertiary">{preview.state_records.length} shown</span>
                  </div>
                  {preview.state_records.length ? (
                    <ul className="mt-2 space-y-2">
                      {preview.state_records.map((record) => (
                        <li key={`${record.namespace}/${record.key}`} className="rounded-control border border-line bg-surface p-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs text-text-tertiary">{record.namespace}</span>
                            <span className="min-w-0 break-all text-sm font-medium text-text-primary">{record.key}</span>
                            <span className="text-xs text-text-tertiary">v{record.version}</span>
                            <span className="ml-auto"><EvidenceTag label={record.evidence_label} /></span>
                          </div>
                          <p className="mt-2 text-xs leading-5 text-text-secondary">
                            {reasonText[record.reason_code] ?? "The record is stored, but its evidence needs interpretation."}
                            {record.storage_status === "locked" ? " Locked." : ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : <p className="mt-2 text-sm text-text-tertiary">No stored state records in this view.</p>}
                </section>

                <section aria-labelledby={`${panelId}-workflows`}>
                  <div className="flex items-center justify-between gap-3">
                    <h4 id={`${panelId}-workflows`} className="text-sm font-medium text-text-primary">Workflow positions</h4>
                    <span className="text-xs text-text-tertiary">{preview.workflow_records.length} shown</span>
                  </div>
                  {preview.workflow_records.length ? (
                    <ul className="mt-2 space-y-2">
                      {preview.workflow_records.map((record) => (
                        <li key={`${record.workflow_id}/${record.run_key}`} className="rounded-control border border-line bg-surface p-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="min-w-0 break-all text-sm font-medium text-text-primary">{record.workflow_id}</span>
                            <span className="text-xs text-text-tertiary">run {record.run_key} · v{record.version}</span>
                            <span className="ml-auto"><EvidenceTag label={record.evidence_label} /></span>
                          </div>
                          <p className="mt-2 text-xs text-text-secondary">Recorded status: {record.recorded_status.replaceAll("_", " ")}</p>
                          <p className="mt-1 text-xs leading-5 text-text-secondary">
                            {record.next_step ? `Next recorded step: ${record.next_step}` : "No next step is recorded."}
                          </p>
                          <p className="mt-1 text-xs leading-5 text-text-tertiary">
                            External execution: unverified. {reasonText[record.reason_code] ?? ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : <p className="mt-2 text-sm text-text-tertiary">No workflow positions in this view.</p>}
                </section>

                <section aria-labelledby={`${panelId}-executions`}>
                  <div className="flex items-center justify-between gap-3">
                    <h4 id={`${panelId}-executions`} className="text-sm font-medium text-text-primary">External execution records</h4>
                    <span className="text-xs text-text-tertiary">{preview.execution_records.length} shown</span>
                  </div>
                  {preview.execution_records.length ? (
                    <ul className="mt-2 space-y-2">
                      {preview.execution_records.map((record) => (
                        <li key={record.execution_id} className="rounded-control border border-line bg-surface p-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-medium text-text-primary">{record.side_effect_status.replaceAll("_", " ")}</span>
                            <span className="ml-auto"><EvidenceTag label={record.evidence_label} /></span>
                          </div>
                          <p className="mt-2 text-xs leading-5 text-text-secondary">
                            Execution: {record.status.replaceAll("_", " ")} · Retry: {record.retry_status.replaceAll("_", " ")}
                          </p>
                          <p className="mt-1 text-xs leading-5 text-text-tertiary">
                            Updated {formatTime(record.updated_at)}. {reasonText[record.reason_code] ?? ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : <p className="mt-2 text-sm text-text-tertiary">No external side-effect execution records are included in this view.</p>}
                </section>
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
                <p className="text-[11px] leading-5 text-text-tertiary">
                  Metadata only · no state values, credentials, tool payloads, or transition evidence.
                </p>
                <span className="font-mono text-[10px] text-text-tertiary" title={preview.state_fingerprint}>
                  Snapshot {preview.state_fingerprint.slice(0, 12)}
                </span>
              </div>
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
