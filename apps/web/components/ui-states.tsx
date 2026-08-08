import { AlertCircle, ArrowRight, LoaderCircle } from "lucide-react";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="panel flex min-h-28 items-center gap-3 p-5 text-sm text-text-secondary" role="status">
      <LoaderCircle aria-hidden className="animate-spin text-accent" size={18} strokeWidth={1.8} />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ title, detail, action }: { title: string; detail: string; action?: React.ReactNode }) {
  return (
    <div className="rounded-card border border-danger/25 bg-surface p-5" role="alert">
      <div className="flex gap-3">
        <AlertCircle aria-hidden className="mt-0.5 shrink-0 text-danger" size={19} strokeWidth={1.8} />
        <div>
          <p className="font-medium text-text-primary">{title}</p>
          <p className="mt-1 text-sm leading-6 text-text-secondary">{detail}</p>
          {action && <div className="mt-4">{action}</div>}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <p className="font-medium text-text-primary">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-text-secondary">{description}</p>
      {action && <div className="mt-4 inline-flex">{action}</div>}
    </div>
  );
}

export function InlineLink({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm font-medium text-accent-hover">
      {children}
      <ArrowRight aria-hidden size={15} strokeWidth={1.8} />
    </span>
  );
}
