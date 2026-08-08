"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiJson } from "@/lib/api";

type Provider = { id: string; configured: boolean; models: string[] };
type Settings = { default_provider: string; default_model: string; providers: Provider[]; mcp: { servers: { id: string; configured: boolean }[] }; secrets: { storage: string; values_exposed: boolean } };

export function SettingsPanel() {
  const [settings, setSettings] = useState<Settings>();
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => { void apiJson<Settings>("/api/settings").then((item) => { setSettings(item); setProvider(item.default_provider); setModel(item.default_model); }); }, []);
  const selected = useMemo(() => settings?.providers.find((item) => item.id === provider), [provider, settings]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const item = await apiJson<Settings>("/api/settings", { method: "PATCH", body: JSON.stringify({ default_provider: provider, default_model: model }) });
    setSettings(item); setSaved(true); window.setTimeout(() => setSaved(false), 1800);
  }

  if (!settings) return <div className="panel p-8 text-sm text-muted">Loading safe configuration…</div>;
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
      <form onSubmit={submit} className="panel p-6"><p className="eyebrow">Model routing</p><h2 className="mt-2 text-2xl font-semibold">Defaults</h2><div className="mt-6 grid gap-4 sm:grid-cols-2"><label className="text-xs font-semibold text-muted">Provider<select className="field mt-2 w-full" value={provider} onChange={(event) => { const id = event.target.value; setProvider(id); setModel(settings.providers.find((item) => item.id === id)?.models[0] || ""); }}>{settings.providers.map((item) => <option key={item.id} value={item.id}>{item.id}</option>)}</select></label><label className="text-xs font-semibold text-muted">Model<select className="field mt-2 w-full" value={model} onChange={(event) => setModel(event.target.value)}>{(selected?.models || []).map((item) => <option key={item} value={item}>{item}</option>)}</select></label></div><button className="button-primary mt-5">{saved ? "Saved" : "Save defaults"}</button></form>
      <div className="space-y-5">
        <section className="panel p-6"><p className="eyebrow">Providers</p><div className="mt-5 space-y-3">{settings.providers.map((item) => <div key={item.id} className="flex items-center justify-between rounded-2xl bg-black/[0.025] p-4"><div><p className="font-semibold capitalize">{item.id}</p><p className="mt-1 text-xs text-muted">{item.models.length} configured model IDs</p></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${item.configured ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{item.configured ? "Ready" : "Key needed"}</span></div>)}</div></section>
        <section className="panel p-6"><p className="eyebrow">Security</p><p className="mt-3 text-sm leading-6 text-muted">Secrets are read from {settings.secrets.storage}. Values exposed to the browser: <strong>{String(settings.secrets.values_exposed)}</strong>.</p><div className="mt-4 rounded-2xl bg-black/[0.025] p-4 text-sm"><span className="mr-2 inline-block size-2 rounded-full bg-emerald-500" />MCP {settings.mcp.servers[0]?.id} connected</div></section>
      </div>
    </div>
  );
}
