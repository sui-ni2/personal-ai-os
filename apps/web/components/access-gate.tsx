"use client";

import { FormEvent, useEffect, useState } from "react";
import { LockKeyhole, Sparkles } from "lucide-react";
import { apiJson } from "@/lib/api";

type AuthStatus = { required: boolean; authenticated: boolean };

const mobilePreview = process.env.NEXT_PUBLIC_PERSONAL_AI_OS_MOBILE_PREVIEW === "true";

function MobilePreview({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div className="fixed inset-x-0 top-0 z-[100] bg-text-primary px-4 py-2 text-center text-[11px] font-medium tracking-[0.01em] text-surface-elevated">
        Mobile UI preview · saved data and AI are not connected in this build
      </div>
      <div className="pt-8">{children}</div>
    </>
  );
}

export function AccessGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState(mobilePreview);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (mobilePreview) return;
    let active = true;
    apiJson<AuthStatus>("/api/auth/status", { cache: "no-store" })
      .then((result) => { if (active) setStatus(result); })
      .catch(() => { if (active) setConnectionError(true); });
    return () => { active = false; };
  }, []);

  async function unlock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiJson<{ authenticated: boolean }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      setPassword("");
      setStatus({ required: true, authenticated: true });
    } catch {
      setError("That password did not work. Check it and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (status?.authenticated) return children;

  if (connectionError && mobilePreview) return <MobilePreview>{children}</MobilePreview>;

  if (!status && !connectionError) {
    return (
      <main className="grid min-h-[100dvh] place-items-center bg-background" aria-busy="true">
        <span className="size-9 animate-pulse rounded-control bg-accent-soft" aria-label="Opening Personal AI OS" />
      </main>
    );
  }

  if (connectionError) {
    return (
      <main className="grid min-h-[100dvh] place-items-center px-5">
        <section className="w-full max-w-[420px] rounded-card border border-line bg-surface p-6 text-center shadow-soft">
          <h1 className="text-xl font-medium">Personal AI OS is unavailable.</h1>
          <p className="mt-2 text-sm leading-6 text-text-secondary">The secure API could not be reached. Check your connection, then try again.</p>
          <button type="button" className="button-secondary mt-5" onClick={() => window.location.reload()}>Try again</button>
        </section>
      </main>
    );
  }

  return (
    <main className="relative grid min-h-[100dvh] place-items-center overflow-hidden px-5 py-10">
      <div className="pointer-events-none absolute left-1/2 top-[-15%] h-[420px] w-[420px] -translate-x-1/2 rounded-full bg-accent-soft/55 blur-3xl" aria-hidden />
      <section className="relative w-full max-w-[420px] rounded-[28px] border border-line bg-surface-elevated p-6 shadow-composer sm:p-8" aria-labelledby="unlock-title">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-control bg-accent-soft text-accent-hover"><Sparkles aria-hidden size={19} /></span>
          <span className="text-sm font-medium">Personal AI OS</span>
        </div>
        <div className="mt-10 grid size-14 place-items-center rounded-card bg-surface-subtle text-accent-hover"><LockKeyhole aria-hidden size={25} strokeWidth={1.7} /></div>
        <h1 id="unlock-title" className="mt-5 text-[30px] font-medium leading-tight tracking-[-0.035em]">Your space is private.</h1>
        <p className="mt-3 text-[15px] leading-6 text-text-secondary">Enter your access password to continue. Model credentials stay on the server and are never sent to this phone.</p>
        <form className="mt-8" onSubmit={unlock}>
          <label htmlFor="access-password" className="text-xs font-medium text-text-secondary">Access password</label>
          <input
            id="access-password"
            type="password"
            autoComplete="current-password"
            required
            autoFocus
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="field mt-2 w-full"
            aria-describedby={error ? "access-error" : undefined}
          />
          {error && <p id="access-error" role="alert" className="mt-3 text-sm text-danger">{error}</p>}
          <button type="submit" className="button-primary mt-5 w-full" disabled={submitting || !password}>
            {submitting ? "Unlocking…" : "Unlock"}
          </button>
        </form>
      </section>
    </main>
  );
}
