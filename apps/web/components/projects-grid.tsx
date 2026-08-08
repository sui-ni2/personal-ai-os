"use client";

import Link from "next/link";
import { useEffect, useState, type ComponentType } from "react";
import { ArrowRight, CircleDot, Code2, FolderKanban, Microscope, Sparkles } from "lucide-react";
import { apiJson } from "@/lib/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui-states";

type Project = { id: string; name: string; description: string; icon: string; status: string };

const iconMap: Record<string, ComponentType<{ size?: number; strokeWidth?: number; className?: string; "aria-hidden"?: boolean }>> = {
  sparkles: Sparkles,
  ball: CircleDot,
  code: Code2,
  research: Microscope,
};

const planned = [
  { id: "codex", name: "Codex", description: "A focused space for software work.", icon: Code2 },
  { id: "research", name: "Research", description: "A focused space for source-based exploration.", icon: Microscope },
];

export function ProjectsGrid() {
  const [items, setItems] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    void apiJson<{ items: Project[] }>("/api/projects")
      .then((data) => setItems(data.items))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState label="Opening your projects" />;
  if (error) return <ErrorState title="Projects are unavailable" detail="The project registry could not be reached. Refresh after the API is running." />;
  if (!items.length) return <EmptyState title="No projects registered" description="Projects will appear here when they are registered through the project contract." />;

  return (
    <div className="space-y-9 sm:space-y-12">
      <section aria-labelledby="active-projects">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Available</p>
            <h2 id="active-projects" className="section-title mt-1">Your projects</h2>
          </div>
          <span className="text-sm text-text-tertiary">{items.length} active</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {items.map((item) => {
            const Icon = iconMap[item.icon] || FolderKanban;
            return (
              <article id={item.id} key={item.id} className="panel flex min-h-[220px] scroll-mt-24 flex-col p-5 sm:min-h-[250px] sm:p-7">
                <div className="flex items-start justify-between gap-4">
                  <span className="grid size-11 place-items-center rounded-control bg-accent-soft text-accent"><Icon aria-hidden size={19} strokeWidth={1.7} /></span>
                  <span className="chip capitalize"><span className="status-dot bg-success" />{item.status}</span>
                </div>
                <h3 className="mt-6 text-xl font-medium tracking-[-0.02em] sm:mt-8">{item.name}</h3>
                <p className="mt-2 flex-1 text-sm leading-6 text-text-secondary">{item.description}</p>
                <div className="mt-6 flex items-center justify-between gap-4 border-t border-line pt-4 sm:mt-7">
                  <span className="text-xs text-text-tertiary">Activity in Repository</span>
                  <Link href={`/chat?project=${encodeURIComponent(item.id)}`} className="button-quiet px-2 text-accent-hover">Open <ArrowRight aria-hidden size={15} /></Link>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="planned-projects">
        <p className="eyebrow">Later</p>
        <h2 id="planned-projects" className="section-title mt-1">Planned spaces</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {planned.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.id} className="rounded-card border border-dashed border-line-strong bg-surface/40 p-4 text-text-tertiary sm:p-5">
                <div className="flex items-center gap-3">
                  <Icon aria-hidden size={18} strokeWidth={1.7} />
                  <h3 className="font-medium text-text-secondary">{item.name}</h3>
                  <span className="chip ml-auto">Planned</span>
                </div>
                <p className="mt-3 text-sm leading-6">{item.description}</p>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
