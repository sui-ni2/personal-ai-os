"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { trapFocus } from "@/lib/focus";
import {
  Archive,
  ChevronLeft,
  Download,
  FolderKanban,
  Home,
  MessageCircle,
  MoreHorizontal,
  NotebookTabs,
  Settings,
  Share,
  SquarePlus,
  Sparkles,
  X,
} from "lucide-react";

const navigation = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/chat", label: "Chat", icon: MessageCircle },
  { href: "/memory", label: "Memory", icon: NotebookTabs },
  { href: "/repository", label: "Outcomes", icon: Archive },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/settings", label: "Settings", icon: Settings },
];

const mobileNavigation = navigation.filter((item) => ["/", "/chat", "/projects"].includes(item.href));

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

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
            <span className="size-2 rounded-full bg-success" aria-hidden /> General
          </Link>
          <Link href="/projects#soccer" onClick={onNavigate} className="flex min-h-10 items-center gap-3 rounded-control px-3 text-sm text-text-secondary hover:bg-surface-subtle/65 hover:text-text-primary">
            <span className="size-2 rounded-full bg-accent" aria-hidden /> Soccer
          </Link>
          <Link href="/projects/p5" onClick={onNavigate} className="flex min-h-10 items-center gap-3 rounded-control px-3 text-sm text-text-secondary hover:bg-surface-subtle/65 hover:text-text-primary">
            <span className="size-2 rounded-full bg-warning" aria-hidden /> P5 / 排列5
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
  const [moreOpen, setMoreOpen] = useState(false);
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [iosInstallAvailable, setIosInstallAvailable] = useState(false);
  const [showInstallHelp, setShowInstallHelp] = useState(false);
  const sheetRef = useRef<HTMLElement>(null);
  const moreTriggerRef = useRef<HTMLButtonElement>(null);
  const focusedChat = pathname.startsWith("/chat");

  useEffect(() => { setMoreOpen(false); setShowInstallHelp(false); }, [pathname]);

  useEffect(() => {
    const handlePrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    const handleInstalled = () => setInstallPrompt(null);
    window.addEventListener("beforeinstallprompt", handlePrompt);
    window.addEventListener("appinstalled", handleInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", handlePrompt);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  useEffect(() => {
    const device = window.navigator as Navigator & { standalone?: boolean };
    const isIos = /iPad|iPhone|iPod/.test(device.userAgent) || (device.platform === "MacIntel" && device.maxTouchPoints > 1);
    const standalone = Boolean(device.standalone) || window.matchMedia("(display-mode: standalone)").matches;
    setIosInstallAvailable(isIos && !standalone);
  }, []);

  useEffect(() => {
    if (!moreOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => sheetRef.current?.querySelector<HTMLElement>("button, a")?.focus());
    return () => { document.body.style.overflow = previous; };
  }, [moreOpen, showInstallHelp]);

  function closeMore() {
    setMoreOpen(false);
    setShowInstallHelp(false);
    window.requestAnimationFrame(() => moreTriggerRef.current?.focus());
  }

  async function installApp() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    if (choice.outcome === "accepted") setInstallPrompt(null);
  }

  function handleMoreKeys(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeMore();
      return;
    }
    trapFocus(event);
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[264px_minmax(0,1fr)]">
      <a href="#main-content" className="fixed left-3 top-3 z-[80] -translate-y-20 rounded-control bg-text-primary px-4 py-3 text-sm text-surface focus:translate-y-0">Skip to content</a>

      <aside className="sticky top-0 hidden h-screen border-r border-line bg-sidebar px-5 py-6 md:block lg:px-6 lg:py-7">
        <SidebarContent pathname={pathname} />
      </aside>

      <main id="main-content" className={`min-w-0 ${focusedChat ? "" : "pb-[calc(76px+env(safe-area-inset-bottom))] md:pb-0"}`}>{children}</main>

      {!focusedChat && (
        <nav className="fixed inset-x-0 bottom-0 z-40 grid h-[calc(66px+env(safe-area-inset-bottom))] grid-cols-4 border-t border-line bg-surface/95 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden" aria-label="Mobile navigation">
          {mobileNavigation.map((item) => {
            const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={`flex min-h-14 flex-col items-center justify-center gap-1 text-[11px] font-medium ${active ? "text-accent-hover" : "text-text-tertiary"}`}>
                <Icon aria-hidden size={20} strokeWidth={active ? 2 : 1.7} /> {item.label}
              </Link>
            );
          })}
          <button ref={moreTriggerRef} onClick={() => setMoreOpen(true)} className="flex min-h-14 flex-col items-center justify-center gap-1 text-[11px] font-medium text-text-tertiary" aria-haspopup="dialog" aria-expanded={moreOpen}>
            <MoreHorizontal aria-hidden size={20} strokeWidth={1.7} /> More
          </button>
        </nav>
      )}

      {moreOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="presentation">
          <button className="absolute inset-0 bg-text-primary/20" tabIndex={-1} aria-label="Close more menu" onClick={closeMore} />
          <aside ref={sheetRef} role="dialog" aria-modal="true" className="absolute inset-x-0 bottom-0 rounded-t-[28px] border-t border-line bg-surface-elevated px-5 pb-[max(24px,env(safe-area-inset-bottom))] pt-4 shadow-composer" aria-label="More destinations" onKeyDown={handleMoreKeys}>
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line-strong" aria-hidden />
            <div className="mb-3 flex items-center justify-between">
              <div className="flex min-w-0 items-center gap-1">
                {showInstallHelp && <button type="button" className="icon-button -ml-2" onClick={() => setShowInstallHelp(false)} aria-label="Back to more destinations"><ChevronLeft aria-hidden size={20} /></button>}
                <h2 className="truncate text-lg font-medium">{showInstallHelp ? "Install on iPhone" : "More"}</h2>
              </div>
              <button className="icon-button" onClick={closeMore} aria-label="Close more menu"><X aria-hidden size={20} /></button>
            </div>
            {showInstallHelp ? (
              <div>
                <p className="text-sm leading-6 text-text-secondary">iPhone installation is handled by Safari. It adds Personal AI OS to your Home Screen without exposing any provider key.</p>
                <ol className="mt-5 space-y-2">
                  <li className="flex min-h-14 items-center gap-3 rounded-control bg-surface-subtle/60 px-4"><Share aria-hidden size={19} className="shrink-0 text-accent-hover" /><span className="text-sm"><strong className="font-medium">1. Open in Safari</strong><span className="mt-0.5 block text-xs text-text-secondary">Then tap the Share button.</span></span></li>
                  <li className="flex min-h-14 items-center gap-3 rounded-control bg-surface-subtle/60 px-4"><SquarePlus aria-hidden size={19} className="shrink-0 text-accent-hover" /><span className="text-sm"><strong className="font-medium">2. Add to Home Screen</strong><span className="mt-0.5 block text-xs text-text-secondary">Scroll the Share menu if needed.</span></span></li>
                  <li className="flex min-h-14 items-center gap-3 rounded-control bg-surface-subtle/60 px-4"><Download aria-hidden size={19} className="shrink-0 text-accent-hover" /><span className="text-sm"><strong className="font-medium">3. Confirm Add</strong><span className="mt-0.5 block text-xs text-text-secondary">The app opens in its own window afterward.</span></span></li>
                </ol>
              </div>
            ) : (
              <div className="grid gap-2">
                {installPrompt && (
                  <button type="button" className="flex min-h-14 items-center gap-3 rounded-control bg-accent-soft px-4 text-left text-sm font-medium text-accent-hover" onClick={() => void installApp()}>
                    <Download aria-hidden size={19} strokeWidth={1.7} /> Install app
                  </button>
                )}
                {!installPrompt && iosInstallAvailable && <button type="button" className="flex min-h-14 items-center gap-3 rounded-control bg-accent-soft px-4 text-left text-sm font-medium text-accent-hover" onClick={() => setShowInstallHelp(true)}><SquarePlus aria-hidden size={19} strokeWidth={1.7} />Install on iPhone</button>}
                {navigation.filter((item) => ["/memory", "/repository", "/settings"].includes(item.href)).map((item) => {
                  const Icon = item.icon;
                  return <Link key={item.href} href={item.href} className="flex min-h-14 items-center gap-3 rounded-control bg-surface-subtle/60 px-4 text-sm font-medium" onClick={closeMore}><Icon aria-hidden size={19} strokeWidth={1.7} />{item.label}</Link>;
                })}
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
