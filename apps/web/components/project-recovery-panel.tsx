"use client";

import { useEffect, useState } from "react";
import { Check, RefreshCw, RotateCcw, ShieldAlert } from "lucide-react";
import { apiJson } from "@/lib/api";

type RecoveryStatus = "clean" | "possibly_interrupted" | "recovery_available" | "insufficient_evidence";
type RecoveryInspection = {
  project_id: string;
  status: RecoveryStatus;
  session_id?: string;
  recovery_version?: number;
  recovery_available: boolean;
  state_changed_since_checkpoint?: boolean;
  message: string;
};
type RecoveryPreview = {
  project_id: string;
  session_id: string;
  recovery_version: number;
  status: "recovery_available";
  state_changed_since_checkpoint: boolean;
  record_counts: { states: number; experiences: number; workflows: number };
  snapshot: unknown;
};

type Props = {
  projectId: string;
  projectName: string;
};

export function ProjectRecoveryPanel({ projectId, projectName }: Props) {
  const [inspection, setInspection] = useState<RecoveryInspection | null>(null);
  const [preview, setPreview] = useState<RecoveryPreview | null>(null);
  const [loading, setLoading] = useState<"inspect" | "preview" | "confirm" | null>("inspect");
  const [error, setError] = useState<string | null>(null);
  const [restored, setRestored] = useState(false);

  async function inspect() {
    setLoading("inspect");
    setError(null);
    try {
      const data = await apiJson<RecoveryInspection>(
        `/api/projects/${encodeURIComponent(projectId)}/recovery`,
      );
      setInspection(data);
      setPreview(null);
      setRestored(false);
    } catch {
      setError("Recovery status could not be checked. Confirm the local API is running, then try again.");
    } finally {
      setLoading(null);
    }
  }

  useEffect(() => {
    void inspect();
  }, [projectId]);

  async function loadPreview() {
    if (!inspection?.session_id) return;
    setLoading("preview");
    setError(null);
    try {
      setPreview(await apiJson<RecoveryPreview>(
        `/api/projects/${encodeURIComponent(projectId)}/recovery/sessions/${encodeURIComponent(inspection.session_id)}/preview`,
      ));
    } catch {
      setError("The recovery preview is no longer available. Refresh status before trying again.");
    } finally {
      setLoading(null);
    }
  }

  async function confirm() {
    if (!preview) return;
    setLoading("confirm");
    setError(null);
    try {
      await apiJson(
        `/api/projects/${encodeURIComponent(projectId)}/recovery/sessions/${encodeURIComponent(preview.session_id)}/confirm`,
        { method: "POST", body: JSON.stringify({ expected_version: preview.recovery_version }) },
      );
      setRestored(true);
      setInspection({
        project_id: projectId,
        status: "clean",
        recovery_available: false,
        message: "Recovery was confirmed. New work resumes from the persisted project state shown above.",
      });
    } catch {
      setError("Recovery changed before confirmation. Refresh status and review the current persisted state again.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <section className="mt-4 border-t border-line pt-4" aria-label={`Restart recovery for ${projectName} (${projectId})`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="eyebrow">Restart recovery</p>
          <p className="mt-1 text-xs leading-5 text-text-secondary">
            {inspection?.message || "Checking persisted recovery evidence…"}
          </p>
        </div>
        <button type="button" className="button-quiet shrink-0 px-2" disabled={loading !== null} onClick={() => void inspect()}>
          <RefreshCw aria-hidden size={14} />
          {loading === "inspect" ? "Checking…" : "Check"}
        </button>
      </div>

      {inspection?.status === "recovery_available" && !preview ? (
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-control bg-warning/10 p-3 text-xs leading-5 text-text-secondary">
          <ShieldAlert aria-hidden size={15} className="shrink-0 text-warning" />
          <span className="flex-1">A prior session has recoverable persisted state. It has not been restored automatically.</span>
          <button type="button" className="button-secondary min-h-9 px-3" disabled={loading !== null} onClick={() => void loadPreview()}>
            <RotateCcw aria-hidden size={14} />
            {loading === "preview" ? "Loading…" : "Preview recovery"}
          </button>
        </div>
      ) : null}

      {preview ? (
        <div className="mt-3 rounded-control border border-line bg-surface/70 p-3">
          <p className="text-xs leading-5 text-text-secondary">
            {preview.record_counts.states} state · {preview.record_counts.experiences} reviewed memory · {preview.record_counts.workflows} workflow
            {preview.record_counts.workflows === 1 ? "" : "s"}. This is a bounded preview from the project&apos;s persisted state.
          </p>
          {preview.state_changed_since_checkpoint ? (
            <p className="mt-2 text-xs leading-5 text-warning">State changed after the checkpoint, so this preview shows the newer persisted records.</p>
          ) : null}
          <pre className="mt-3 max-h-56 overflow-auto rounded-control border border-line bg-surface-subtle p-3 text-[11px] leading-5 text-text-secondary">{JSON.stringify(preview.snapshot, null, 2)}</pre>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="button-primary min-h-10 px-3" disabled={loading !== null || restored} onClick={() => void confirm()}>
              <Check aria-hidden size={14} />
              {loading === "confirm" ? "Confirming…" : restored ? "Recovery confirmed" : "Confirm and resume"}
            </button>
            <button type="button" className="button-quiet min-h-10 px-3" disabled={loading !== null} onClick={() => void inspect()}>Discard preview</button>
          </div>
        </div>
      ) : null}

      {inspection && inspection.status !== "clean" && inspection.status !== "recovery_available" ? (
        <p className="mt-2 text-xs leading-5 text-text-tertiary">No recovery is offered until a persisted checkpoint and authoritative project records are both available.</p>
      ) : null}
      {error ? <p className="mt-2 text-xs leading-5 text-danger">{error}</p> : null}
    </section>
  );
}
