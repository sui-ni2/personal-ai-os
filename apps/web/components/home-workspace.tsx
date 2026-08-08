"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarDays, FolderKanban, MessageCircle, Plus } from "lucide-react";
import { apiJson } from "@/lib/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui-states";

type Conversation = {
  id: string;
  title: string;
  provider: string;
  model: string;
  project_id?: string;
  updated_at: string;
};

type Project = { id: string; name: string; description: string; status: string };

function greetingFor(hour: number) {
  if (hour < 12) return "Good morning.";
  if (hour < 18) return "Good afternoon.";
  return "Good evening.";
}

export function HomeWorkspace() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const now = useMemo(() => new Date(), []);

  useEffect(() => {
    void Promise.all([
      apiJson<{ items: Conversation[] }>("/api/conversations"),
      apiJson<{ items: Project[] }>("/api/projects"),
    ])
      .then(([conversationData, projectData]) => {
        setConversations(conversationData.items.slice(0, 3));
        setProjects(projectData.items.slice(0, 4));
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-frame max-w-[1120px] sm:pt-16">
      <header className="mb-12 sm:mb-16">
        <p className="text-sm text-text-tertiary">
          {new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" }).format(now)}
        </p>
        <h1 className="mt-2 text-[30px] font-medium leading-tight tracking-[-0.035em] sm:text-[34px]">
          {greetingFor(now.getHours())}
        </h1>
        <p className="mt-3 max-w-xl text-[15px] leading-6 text-text-secondary">Pick up where you left off, or begin with a clear space.</p>
      </header>

      {loading && <LoadingState label="Opening your workspace" />}
      {!loading && error && <ErrorState title="Your workspace is unavailable" detail="The local API could not be reached. Start the service, then refresh this page." />}

      {!loading && !error && (
        <div className="space-y-12 sm:space-y-14">
          <section aria-labelledby="continue-heading">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <p className="eyebrow">Continue</p>
                <h2 id="continue-heading" className="section-title mt-1">Recent conversations</h2>
              </div>
              <Link href="/chat" className="button-quiet">
                View chat <ArrowRight aria-hidden size={16} strokeWidth={1.8} />
              </Link>
            </div>
            {conversations.length === 0 ? (
              <EmptyState
                title="A fresh start"
                description="There are no conversations yet. Your first chat will appear here when it is saved."
                action={<Link href="/chat" className="button-primary"><Plus aria-hidden size={17} />New chat</Link>}
              />
            ) : (
              <div className="grid gap-3 md:grid-cols-3">
                {conversations.map((item) => (
                  <Link key={item.id} href="/chat" className="group panel p-5 transition-colors duration-150 hover:bg-surface-elevated">
                    <MessageCircle aria-hidden className="text-accent" size={19} strokeWidth={1.7} />
                    <h3 className="mt-5 truncate text-[15px] font-medium">{item.title}</h3>
                    <p className="mt-1 text-xs text-text-tertiary">{item.project_id || "General"} · {new Date(item.updated_at).toLocaleDateString()}</p>
                  </Link>
                ))}
              </div>
            )}
          </section>

          <section aria-labelledby="projects-heading">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <p className="eyebrow">Projects</p>
                <h2 id="projects-heading" className="section-title mt-1">Your spaces</h2>
              </div>
              <Link href="/projects" className="button-quiet">All projects <ArrowRight aria-hidden size={16} strokeWidth={1.8} /></Link>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {projects.map((item) => (
                <Link key={item.id} href={`/projects#${item.id}`} className="panel flex min-h-28 items-start gap-4 p-5 transition-colors duration-150 hover:bg-surface-elevated">
                  <span className="grid size-10 shrink-0 place-items-center rounded-control bg-accent-soft text-accent">
                    <FolderKanban aria-hidden size={18} strokeWidth={1.7} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[15px] font-medium">{item.name}</span>
                    <span className="mt-1 block line-clamp-2 text-sm leading-6 text-text-secondary">{item.description}</span>
                  </span>
                </Link>
              ))}
            </div>
          </section>

          <div className="grid gap-8 md:grid-cols-[1fr_320px]">
            <section aria-labelledby="today-heading">
              <p className="eyebrow">Today</p>
              <h2 id="today-heading" className="section-title mt-1">A quiet slate</h2>
              <div className="mt-4 rounded-card border border-line bg-surface/55 p-5">
                <div className="flex gap-3">
                  <CalendarDays aria-hidden className="mt-0.5 shrink-0 text-text-tertiary" size={18} strokeWidth={1.7} />
                  <div>
                    <p className="font-medium">No tasks connected</p>
                    <p className="mt-1 text-sm leading-6 text-text-secondary">Tasks are planned, but no task source is configured yet.</p>
                  </div>
                </div>
              </div>
            </section>
            <section aria-labelledby="quick-heading">
              <p className="eyebrow">Quick start</p>
              <h2 id="quick-heading" className="section-title mt-1">Begin with a thought</h2>
              <Link href="/chat" className="mt-4 flex min-h-20 items-center justify-between rounded-card bg-accent px-5 text-surface-elevated transition-colors duration-150 hover:bg-accent-hover">
                <span className="font-medium">New chat</span>
                <Plus aria-hidden size={19} strokeWidth={1.8} />
              </Link>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
