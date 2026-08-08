"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Cpu, X } from "lucide-react";

export type ProviderOption = { id: string; configured: boolean; models: string[] };

function displayName(model: string) {
  return model
    .split("-")
    .map((part) => (/^\d/.test(part) ? part : part.charAt(0).toUpperCase() + part.slice(1)))
    .join(" ");
}

function providerName(provider: string) {
  if (provider.toLowerCase() === "openai") return "OpenAI";
  if (provider.toLowerCase() === "anthropic") return "Anthropic";
  return provider.charAt(0).toUpperCase() + provider.slice(1);
}

export function ModelSelector({
  providers,
  provider,
  model,
  onChange,
}: {
  providers: ProviderOption[];
  provider: string;
  model: string;
  onChange: (provider: string, model: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const first = panelRef.current?.querySelector<HTMLElement>("button:not([disabled])");
    first?.focus();
  }, [open]);

  function handleKeys(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(panelRef.current?.querySelectorAll<HTMLElement>("button:not([disabled])") || []);
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
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        className="flex min-h-11 max-w-[220px] items-center gap-2 rounded-control px-3 text-left transition-colors duration-150 hover:bg-surface-subtle"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <Cpu aria-hidden size={17} strokeWidth={1.7} className="shrink-0 text-text-tertiary" />
        <span className="min-w-0">
          <span className="block truncate text-xs text-text-tertiary">Model</span>
          <span className="block truncate text-sm font-medium">{model ? displayName(model) : "Choose model"}</span>
        </span>
        <ChevronDown aria-hidden size={15} className="ml-auto shrink-0 text-text-tertiary" />
      </button>

      {open && (
        <>
          <button className="fixed inset-0 z-50 cursor-default bg-text-primary/10 sm:bg-transparent" onClick={() => setOpen(false)} aria-label="Close model selector" />
          <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Choose a model"
            onKeyDown={handleKeys}
            className="fixed inset-x-0 bottom-0 z-[60] max-h-[78vh] overflow-y-auto rounded-t-large border border-line bg-surface-elevated p-4 shadow-composer sm:absolute sm:inset-auto sm:left-0 sm:top-[calc(100%+8px)] sm:w-[360px] sm:rounded-card sm:p-3"
          >
            <div className="mb-3 flex items-center justify-between px-1 sm:px-2">
              <div>
                <p className="text-sm font-medium">Choose model</p>
                <p className="mt-0.5 text-xs text-text-tertiary">Models are provided by your configured adapters.</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setOpen(false)} aria-label="Close model selector">
                <X aria-hidden size={18} />
              </button>
            </div>
            <div className="space-y-4">
              {providers.map((item) => (
                <section key={item.id} aria-labelledby={`provider-${item.id}`}>
                  <div className="flex items-center justify-between px-2 py-1">
                    <h3 id={`provider-${item.id}`} className="text-xs font-medium uppercase tracking-[0.1em] text-text-tertiary">{providerName(item.id)}</h3>
                    <span className={`text-xs font-medium ${item.configured ? "text-success" : "text-text-tertiary"}`}>
                      {item.configured ? "Configured" : "Not configured"}
                    </span>
                  </div>
                  <div className="mt-1 space-y-1">
                    {item.models.map((candidate) => {
                      const selected = item.id === provider && candidate === model;
                      return (
                        <button
                          key={candidate}
                          type="button"
                          className={`flex min-h-14 w-full items-center gap-3 rounded-control px-3 py-2 text-left transition-colors duration-150 ${selected ? "bg-accent-soft" : "hover:bg-surface-subtle"}`}
                          onClick={() => {
                            onChange(item.id, candidate);
                            setOpen(false);
                            triggerRef.current?.focus();
                          }}
                        >
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium">{displayName(candidate)}</span>
                            <span className="mt-0.5 block truncate text-xs text-text-tertiary">{candidate}</span>
                          </span>
                          {selected && <Check aria-label="Selected" size={17} className="shrink-0 text-accent" strokeWidth={2} />}
                        </button>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
