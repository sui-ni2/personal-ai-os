"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CalendarDays,
  Clock3,
  MessageCircle,
  Mic2,
  NotebookTabs,
  Sparkles,
} from "lucide-react";
import { apiJson } from "@/lib/api";

type Conversation = { id: string; title: string; project_id?: string; updated_at: string };
type Memory = { id: string };
type RepositoryEvent = { id: string; summary: string; created_at: string };

function greetingFor(hour: number) {
  if (hour < 12) return "Good morning.";
  if (hour < 18) return "Good afternoon.";
  return "Good evening.";
}

function timeAgo(value: string) {
  const elapsed = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.round(elapsed / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function HomeWorkspace() {
  const [mode, setMode] = useState<"text" | "live">("text");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [memoryCount, setMemoryCount] = useState(0);
  const [recentEvent, setRecentEvent] = useState<RepositoryEvent>();
  const [connected, setConnected] = useState(true);
  const now = useMemo(() => new Date(), []);

  useEffect(() => {
    void Promise.all([
      apiJson<{ items: Conversation[] }>("/api/conversations"),
      apiJson<{ items: Memory[] }>("/api/memory?status=active"),
      apiJson<{ items: RepositoryEvent[] }>("/api/repository/timeline"),
    ])
      .then(([conversationData, memoryData, timelineData]) => {
        setConversations(conversationData.items.slice(0, 3));
        setMemoryCount(memoryData.items.length);
        setRecentEvent(timelineData.items[0]);
      })
      .catch(() => setConnected(false));
  }, []);

  const startHref = `/chat?new=1&mode=${mode}`;

  return (
    <div className="mx-auto min-h-screen w-full max-w-[1040px] px-5 pb-8 pt-[max(22px,env(safe-area-inset-top))] sm:px-9 sm:pt-12 lg:px-12">
      <header className="flex items-center justify-between">
        <Link href="/" className="flex min-h-11 items-center gap-2.5 rounded-control text-sm font-medium tracking-[-0.01em]">
          <span className="grid size-9 place-items-center rounded-full bg-accent-soft text-accent-hover"><Sparkles aria-hidden size={17} /></span>
          Personal AI OS
        </Link>
        <Link href="/settings" aria-label="Open settings" className="grid size-10 place-items-center rounded-full border border-line bg-surface text-xs font-semibold text-accent-hover shadow-soft">You</Link>
      </header>

      <main className="pt-10 sm:pt-14">
        <p className="text-[13px] font-medium tracking-[0.01em] text-text-tertiary">
          {new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" }).format(now)}
        </p>
        <h1 className="mt-2 text-[34px] font-medium leading-[1.08] tracking-[-0.045em] sm:text-[42px]">{greetingFor(now.getHours())}</h1>
        <p className="mt-3 text-[15px] leading-6 text-text-secondary">What would you like to move forward?</p>

        <div className="relative mt-4 aspect-[16/7] min-h-[150px] w-full overflow-hidden rounded-[24px] sm:mt-6 sm:aspect-[2.65/1]">
          <Image src="/assets/personal-ai-flow.png" alt="" fill priority sizes="(max-width: 768px) 100vw, 780px" className="object-cover" />
        </div>

        <section className="mx-auto -mt-2 max-w-[720px] sm:-mt-3" aria-labelledby="start-heading">
          <h2 id="start-heading" className="sr-only">Start a conversation</h2>
          <div className="grid grid-cols-2 rounded-full bg-surface-subtle p-1" role="group" aria-label="Conversation mode">
            <button type="button" onClick={() => setMode("text")} aria-pressed={mode === "text"} className={`flex min-h-11 items-center justify-center gap-2 rounded-full text-sm font-medium transition ${mode === "text" ? "bg-surface-elevated text-text-primary shadow-soft" : "text-text-secondary"}`}><MessageCircle aria-hidden size={16} /> Text</button>
            <button type="button" onClick={() => setMode("live")} aria-pressed={mode === "live"} className={`flex min-h-11 items-center justify-center gap-2 rounded-full text-sm font-medium transition ${mode === "live" ? "bg-surface-elevated text-text-primary shadow-soft" : "text-text-secondary"}`}><Mic2 aria-hidden size={16} /> GPT Live</button>
          </div>
          <Link href={startHref} className="mt-3 flex min-h-14 w-full items-center justify-center gap-2 rounded-[18px] bg-text-primary px-5 text-[15px] font-medium text-surface-elevated transition hover:bg-accent-hover">
            {mode === "text" ? <MessageCircle aria-hidden size={18} /> : <Mic2 aria-hidden size={18} />}
            Start a conversation
          </Link>
          <p className="mt-2 text-center text-xs leading-5 text-text-tertiary">{mode === "text" ? "Write first. The title becomes a short summary after your first message." : "Voice starts only after you confirm microphone access."}</p>
        </section>

        {!connected && <p className="mt-8 rounded-control border border-warning/25 bg-surface px-4 py-3 text-sm text-warning">The local service is offline. Your navigation still works, but saved context is temporarily unavailable.</p>}

        <div className="mt-10 divide-y divide-line border-y border-line sm:mt-12">
          <Link href="/chat" className="group flex min-h-[78px] items-center gap-4 py-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-full bg-accent-soft text-accent-hover"><CalendarDays aria-hidden size={18} /></span>
            <span className="min-w-0 flex-1"><span className="block text-sm font-medium">Today</span><span className="mt-1 block truncate text-sm text-text-secondary">{conversations[0] ? `Continue “${conversations[0].title}”` : "No conversation planned yet"}</span></span>
            <ArrowRight aria-hidden className="text-text-tertiary transition-transform group-hover:translate-x-1" size={18} />
          </Link>
          <Link href="/memory" className="group flex min-h-[78px] items-center gap-4 py-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-full bg-surface-subtle text-text-secondary"><NotebookTabs aria-hidden size={18} /></span>
            <span className="min-w-0 flex-1"><span className="block text-sm font-medium">Memory</span><span className="mt-1 block truncate text-sm text-text-secondary">{memoryCount ? `${memoryCount} active memories ready for context` : "No saved memory yet"}</span></span>
            <ArrowRight aria-hidden className="text-text-tertiary transition-transform group-hover:translate-x-1" size={18} />
          </Link>
          <Link href="/repository" className="group flex min-h-[78px] items-center gap-4 py-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-full bg-surface-subtle text-text-secondary"><Clock3 aria-hidden size={18} /></span>
            <span className="min-w-0 flex-1"><span className="block text-sm font-medium">Recent activity</span><span className="mt-1 block truncate text-sm text-text-secondary">{recentEvent ? `${recentEvent.summary} · ${timeAgo(recentEvent.created_at)}` : "Nothing recorded yet"}</span></span>
            <ArrowRight aria-hidden className="text-text-tertiary transition-transform group-hover:translate-x-1" size={18} />
          </Link>
        </div>
      </main>
    </div>
  );
}
