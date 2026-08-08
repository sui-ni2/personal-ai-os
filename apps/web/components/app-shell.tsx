"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  Archive,
  FolderKanban,
  Home,
  Menu,
  MessageCircle,
  NotebookTabs,
  Settings,
  Sparkles,
  X,
} from "lucide-react";

const navigation = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/chat", label: "Chat", icon: MessageCircle },
  { href: "/memory", label: "Memory", icon: NotebookTabs },
  { href: "/repository", label: "Repository", icon: Archive },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/settings", label: "Settings", icon: Settings },
];

function SidebarContent({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <Link href="/" className="flex min-h-12 items-center gap-3 rounded-control" onClick={onNavigate}>
        <span className="grid size-9 place-items-center rounded-control bg-accent-soft text-accent">
          <Sparkles aria-hidden size={17} strokeWidth={1.8} />
        </span>
        <span className="text-[15px] font-medium tracking-[-0.01em]">Personal AI OS</span>
      </Link>

      <nav className="mt-10 space-y-1" aria-label="Primary navigation">
        {navigation.map((item) => {
          const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
              className={`flex min-h-11 items-center gap-3 rounded-control px-3 text-sm font-medium transition-colors duration-150 ${
                active
                  ? "bg-surface-subtle text-text-primary"
                  : "text-text-secondary hover:bg-surface-subtle/65 hover:text-text-primary"
              }`}
            >
              <Icon aria-hidden size={18} strokeWidth={1.7} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-9 border-t border-line pt-6">
        <p className="px-3 text-xs font-medium uppercase tracking-[0.12em] text-text-tertiary">Projects</p>
        <div className="mt-2 space-y-1">
          <Link href="/projects#general" onClick={onNavigate} className="flex min-h-10 items-center gap-3 rounded-control px-3 text-sm text-text-secondary hover:bg-surface-subtle/65 hover:text-text-primary">
            <span className="size-2 rounded-full bg-success" aria-hidden />
            General
          </Link>
          <Link href="/projects#soccer" onClick={onNavigate} className="flex min-h-10 items-center gap-3 rounded-control px-3 text-sm text-text-secondary hover:bg-surface-subtle/65 hover:text-text-primary">
            <span className="size-2 rounded-full bg-accent" aria-hidden />
            Soccer
          </Link>
        </div>
      </div>

      <div className="mt-auto pt-8">
        <div className="rounded-card border border-line bg-surface/55 p-4">
          <p className="text-xs font-medium text-text-primary">Your quiet AI workspace</p>
          <p className="mt-1 text-xs leading-5 text-text-tertiary">Projects stay modular. Your context stays with you.</p>
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLElement>(null);
  const drawerTriggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => drawerRef.current?.querySelector<HTMLElement>("button, a")?.focus());
    return () => {
      document.body.style.overflow = previous;
    };
  }, [drawerOpen]);

  function closeDrawer() {
    setDrawerOpen(false);
    window.requestAnimationFrame(() => drawerTriggerRef.current?.focus());
  }

  function handleDrawerKeys(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeDrawer();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(drawerRef.current?.querySelectorAll<HTMLElement>("button:not([disabled]), a[href]") || []);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[264px_minmax(0,1fr)]">
      <a href="#main-content" className="fixed left-3 top-3 z-[80] -translate-y-20 rounded-control bg-text-primary px-4 py-3 text-sm text-surface focus:translate-y-0">
        Skip to content
      </a>

      <aside className="sticky top-0 hidden h-screen border-r border-line bg-sidebar px-5 py-6 md:block lg:px-6 lg:py-7">
        <SidebarContent pathname={pathname} />
      </aside>

      <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-line bg-background/95 px-4 backdrop-blur-sm md:hidden">
        <Link href="/" className="flex min-h-11 items-center gap-2.5 rounded-control font-medium">
          <span className="grid size-8 place-items-center rounded-control bg-accent-soft text-accent">
            <Sparkles aria-hidden size={16} strokeWidth={1.8} />
          </span>
          Personal AI OS
        </Link>
        <button ref={drawerTriggerRef} className="icon-button" onClick={() => setDrawerOpen(true)} aria-label="Open navigation" aria-expanded={drawerOpen}>
          <Menu aria-hidden size={21} strokeWidth={1.7} />
        </button>
      </header>

      {drawerOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="presentation">
          <button className="absolute inset-0 bg-text-primary/20" tabIndex={-1} aria-label="Close navigation" onClick={closeDrawer} />
          <aside ref={drawerRef} role="dialog" aria-modal="true" onKeyDown={handleDrawerKeys} className="absolute inset-y-0 left-0 w-[min(310px,86vw)] border-r border-line bg-sidebar px-5 py-5 shadow-soft" aria-label="Mobile navigation">
            <div className="mb-5 flex justify-end">
              <button className="icon-button" onClick={closeDrawer} aria-label="Close navigation">
                <X aria-hidden size={21} strokeWidth={1.7} />
              </button>
            </div>
            <SidebarContent pathname={pathname} onNavigate={closeDrawer} />
          </aside>
        </div>
      )}

      <main id="main-content" className="min-w-0">{children}</main>
    </div>
  );
}
