"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/chat", label: "Chat", icon: "✦" },
  { href: "/memory", label: "Memory", icon: "◇" },
  { href: "/repository", label: "Repository", icon: "▤" },
  { href: "/projects", label: "Projects", icon: "◫" },
  { href: "/settings", label: "Settings", icon: "⚙" }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <aside className="hidden border-r border-black/5 px-6 py-8 md:flex md:flex-col">
        <Link href="/chat" className="mb-12 block">
          <span className="eyebrow">Personal</span>
          <span className="mt-1 block text-2xl font-semibold tracking-tight">AI OS</span>
        </Link>
        <nav className="space-y-2" aria-label="Primary navigation">
          {navigation.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} className={`flex min-h-12 items-center gap-3 rounded-2xl px-4 text-sm font-medium transition ${active ? "bg-ink text-white" : "text-muted hover:bg-white/60 hover:text-ink"}`}>
                <span aria-hidden>{item.icon}</span>{item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto rounded-3xl bg-white/55 p-4 text-xs leading-5 text-muted">
          V0.1 modular monolith<br />Traceable, project-neutral core.
        </div>
      </aside>
      <main className="min-w-0 pb-24 md:pb-0">{children}</main>
      <nav className="fixed inset-x-3 bottom-3 z-50 grid grid-cols-5 rounded-3xl border border-black/5 bg-card/95 p-2 shadow-soft backdrop-blur md:hidden" aria-label="Mobile navigation">
        {navigation.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-2xl text-[10px] font-medium ${active ? "bg-ink text-white" : "text-muted"}`}>
              <span className="text-base" aria-hidden>{item.icon}</span>{item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
