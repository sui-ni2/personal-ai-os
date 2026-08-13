import {
  AlertCircle,
  Cable,
  CheckCircle2,
  ChevronDown,
  Cpu,
  FileText,
  Wrench,
} from "lucide-react";
import type { SseEvent } from "@/lib/api";

const iconMap = {
  message: Cpu,
  tool_start: Wrench,
  tool_result: Cable,
  error: AlertCircle,
  done: CheckCircle2,
};

function actionLabel(item: SseEvent) {
  if (item.type === "tool_start") return item.tool ? `Using ${item.tool}` : "Tool started";
  if (item.type === "tool_result") return item.tool ? `${item.tool} finished` : "Tool finished";
  if (item.type === "error") return "Action needs attention";
  if (item.type === "done") return "Response completed";
  return "Model responded";
}

function actionSummary(item: SseEvent) {
  if (item.type === "error") return "Check AI service or tool settings, then try again.";
  if (typeof item.duration_ms === "number") return `${item.duration_ms} ms`;
  if (item.status === "running" || item.status === "started") return "In progress";
  return item.status === "succeeded" ? "Completed" : "Recorded";
}

function safePayload(payload: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(payload).filter(([key]) => !/(trace|stack|exception|reasoning|thought)/i.test(key)),
  );
}

export function ActivityPanel({ trace }: { trace: SseEvent[] }) {
  const actions = trace.filter((item) => item.type !== "message");
  const complete = actions.filter((item) => item.status === "succeeded").length;

  return (
    <details className="group border-t border-line bg-surface/55">
      <summary className="mx-auto flex min-h-12 w-full max-w-[780px] cursor-pointer list-none items-center gap-2 px-4 text-sm text-text-secondary sm:px-6">
        <CheckCircle2 aria-hidden size={16} className={actions.length ? "text-success" : "text-text-tertiary"} strokeWidth={1.8} />
        <span className="font-medium text-text-primary">Activity</span>
        <span>{actions.length ? `${complete}/${actions.length} actions complete` : "No actions yet"}</span>
        <ChevronDown aria-hidden size={16} className="ml-auto transition-transform duration-150 group-open:rotate-180" />
      </summary>
      <div className="mx-auto max-w-[780px] px-4 pb-5 sm:px-6">
        {actions.length === 0 ? (
          <p className="rounded-control bg-surface-subtle/65 px-4 py-3 text-sm leading-6 text-text-secondary">AI service, tool, retry, error, and completion events will appear here.</p>
        ) : (
          <ol className="space-y-2" aria-label="Execution activity">
            {actions.map((item) => {
              const Icon = item.type === "error" ? AlertCircle : iconMap[item.type] || FileText;
              return (
                <li key={item.id} className="rounded-control border border-line bg-surface-elevated px-3.5 py-3">
                  <div className="flex items-start gap-3">
                    <span className={`mt-0.5 grid size-8 shrink-0 place-items-center rounded-small ${item.type === "error" ? "bg-danger/10 text-danger" : "bg-surface-subtle text-text-secondary"}`}>
                      <Icon aria-hidden size={16} strokeWidth={1.8} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <p className="text-sm font-medium">{actionLabel(item)}</p>
                        <span className="text-xs text-text-tertiary">{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                      <p className="mt-0.5 text-xs leading-5 text-text-secondary">{actionSummary(item)}</p>
                      {Object.keys(safePayload(item.payload)).length > 0 && (
                        <details className="mt-2">
                          <summary className="cursor-pointer text-xs font-medium text-text-tertiary hover:text-text-primary">Show details</summary>
                          <pre className="scrollbar-subtle mt-2 max-h-44 overflow-auto rounded-small bg-surface-subtle p-3 font-mono text-[11px] leading-5 text-text-secondary">{JSON.stringify(safePayload(item.payload), null, 2)}</pre>
                        </details>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </details>
  );
}
