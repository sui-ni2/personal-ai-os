"use client";

import { FormEvent, useEffect, useState } from "react";
import { AlertTriangle, Check, DatabaseBackup, Download, HeartPulse, ShieldCheck, Trash2, WalletCards } from "lucide-react";
import { apiJson } from "@/lib/api";

type Provider = { id: string; configured: boolean; models: string[] };
type Usage = { items: { provider: string; model: string; requests: number; input_tokens: number; output_tokens: number; token_precision: string; cost_precision: string; latency_ms: number }[] };
type Budget = { policies: { period: string; limit_tokens: number; used_tokens: number; warn: boolean; blocked: boolean }[] };
type Routing = { policy: "STRICT_PROVIDER" | "FALLBACK_ALLOWED" | "ASK_BEFORE_FALLBACK"; fallback_provider?: string; fallback_model?: string };
type DoctorReport = { safe_to_share: boolean; database: { status: string; migration_version: number | null } };

export function SettingsGovernancePanel({ providers }: { providers: Provider[] }) {
  const [usage, setUsage] = useState<Usage>({ items: [] });
  const [budget, setBudget] = useState<Budget>({ policies: [] });
  const [routing, setRouting] = useState<Routing>({ policy: "STRICT_PROVIDER" });
  const [period, setPeriod] = useState("daily");
  const [limitTokens, setLimitTokens] = useState("100000");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState("");
  const [lifecycleNotice, setLifecycleNotice] = useState("");
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const [eraseConfirmation, setEraseConfirmation] = useState("");
  const configured = providers.filter((item) => item.configured);

  async function load() {
    const [nextUsage, nextBudget, nextRouting] = await Promise.all([
      apiJson<Usage>("/api/usage?project_id=general"),
      apiJson<Budget>("/api/budgets?project_id=general"),
      apiJson<Routing>("/api/routing"),
    ]);
    setUsage(nextUsage);
    setBudget(nextBudget);
    setRouting(nextRouting);
  }

  useEffect(() => { void load().catch(() => { /* Core Settings stays usable without these optional reads. */ }); }, []);

  async function saveBudget(event: FormEvent) {
    event.preventDefault();
    const limit = Number(limitTokens);
    if (!Number.isInteger(limit) || limit < 1 || saving) return;
    if (!window.confirm("A hard budget stops new requests when the estimated token limit is reached. Save this project budget?")) return;
    setSaving(true);
    try {
      await apiJson("/api/budgets", { method: "PUT", body: JSON.stringify({ scope_type: "project", scope_id: "general", period, limit_tokens: limit, warn_percent: 80, hard_limit: true }) });
      setSaved("Budget saved");
      await load();
    } finally { setSaving(false); }
  }

  async function saveRouting(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const fallback = routing.policy === "STRICT_PROVIDER" ? {} : { fallback_provider: routing.fallback_provider || null, fallback_model: routing.fallback_model || null };
      await apiJson<Routing>("/api/routing", { method: "PUT", body: JSON.stringify({ policy: routing.policy, ...fallback }) });
      setSaved("Routing policy saved");
      await load();
    } finally { setSaving(false); }
  }

  function downloadJson(filename: string, value: object) {
    const url = window.URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 0);
  }

  async function downloadCoreExport() {
    setLifecycleBusy(true);
    try {
      downloadJson("personal-ai-os-core-data-export.json", await apiJson<object>("/api/data/core-export"));
      setLifecycleNotice("Core data export downloaded. Review its excluded scopes before any erase.");
    } catch {
      setLifecycleNotice("Core data export could not be created. Your local data was not changed.");
    } finally { setLifecycleBusy(false); }
  }

  async function downloadDoctorReport() {
    setLifecycleBusy(true);
    try {
      const report = await apiJson<DoctorReport>("/api/doctor");
      downloadJson("personal-ai-os-doctor-safe-report.json", report);
      setLifecycleNotice(report.safe_to_share ? "Redacted Doctor report downloaded." : "Doctor report was not marked safe to share.");
    } catch {
      setLifecycleNotice("Doctor report could not be created. Your local data was not changed.");
    } finally { setLifecycleBusy(false); }
  }

  async function eraseCoreData() {
    if (eraseConfirmation !== "ERASE_CORE_DATA" || lifecycleBusy) return;
    if (!window.confirm("Erase core conversations, memory, project metadata, usage, governance receipts, and connector metadata? Private project databases, files, backups, and credentials will remain.")) return;
    setLifecycleBusy(true);
    try {
      await apiJson("/api/data/core-erase", { method: "POST", body: JSON.stringify({ confirmation: "ERASE_CORE_DATA", export_acknowledged: true }) });
      setEraseConfirmation("");
      setLifecycleNotice("Core database data was erased. The retained scopes are listed below.");
      await load();
    } catch {
      setLifecycleNotice("Core data erase was not completed. Review the export and local API status before retrying.");
    } finally { setLifecycleBusy(false); }
  }

  return (
    <section id="privacy-usage-settings" className="scroll-mt-6 space-y-4" aria-labelledby="privacy-usage-title">
      <div className="flex items-center gap-2"><ShieldCheck aria-hidden size={18} className="text-text-tertiary" /><h2 id="privacy-usage-title" className="section-title">Memory, privacy, usage & budget</h2></div>
      <div className="grid gap-4 lg:grid-cols-2">
        <article className="panel p-4 sm:p-5"><h3 className="text-[15px] font-medium">Memory & privacy</h3><p className="mt-2 text-sm leading-6 text-text-secondary">Long-term Memory is explicit, project-scoped or global, and separate from Outcomes. A send-scope receipt lists the project, provider, reviewed-memory references, tools, and estimated context size for every text request. Secrets and hidden reasoning are excluded.</p><a className="button-quiet mt-4 px-0 text-accent-hover" href="/memory">Review retained memory</a></article>
        <article className="panel p-4 sm:p-5"><h3 className="text-[15px] font-medium">Core data export & erase</h3><p className="mt-2 text-sm leading-6 text-text-secondary">Download the portable core database before erasing it. Credentials, connector targets, private project state, project-native stores, files, and backup archives are excluded and are never claimed as erased by this control.</p><div className="mt-4 flex flex-wrap gap-3"><button type="button" className="button-quiet px-0 text-accent-hover" onClick={() => void downloadCoreExport()} disabled={lifecycleBusy}><Download aria-hidden size={15} />Download core export</button><a className="button-quiet px-0 text-accent-hover" href="/repository">Review files and activity</a></div><label className="mt-4 block text-xs font-medium text-text-secondary">Type <code>ERASE_CORE_DATA</code> to erase only the core database<input className="field mt-1.5 w-full" aria-label="Core data erase confirmation" value={eraseConfirmation} onChange={(event) => setEraseConfirmation(event.target.value)} autoComplete="off" /></label><button type="button" className="button-secondary mt-2 text-danger" onClick={() => void eraseCoreData()} disabled={lifecycleBusy || eraseConfirmation !== "ERASE_CORE_DATA"}><Trash2 aria-hidden size={15} />Erase core data</button></article>
        <article className="panel p-4 sm:p-5"><div className="flex items-center gap-2"><WalletCards aria-hidden size={17} className="text-text-tertiary" /><h3 className="text-[15px] font-medium">Usage & budget</h3></div><p className="mt-2 text-xs leading-5 text-text-secondary">Token figures are estimated unless a provider supplies reliable usage. Provider cost is shown as unknown until it is reliable; it is never presented as a bill.</p>{usage.items.length ? <dl className="mt-4 space-y-2 text-sm">{usage.items.map((item) => <div key={`${item.provider}-${item.model}`} className="flex justify-between gap-3 rounded-small bg-surface-subtle px-3 py-2"><dt>{item.provider} / {item.model}</dt><dd className="text-text-secondary">{item.requests} requests · {item.input_tokens + item.output_tokens} {item.token_precision.toLowerCase()} tokens</dd></div>)}</dl> : <p className="mt-4 text-sm text-text-tertiary">No usage recorded yet.</p>}<form className="mt-4 grid gap-2 sm:grid-cols-[1fr_1fr_auto]" onSubmit={saveBudget}><select className="field" aria-label="Budget period" value={period} onChange={(event) => setPeriod(event.target.value)}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select><input className="field" aria-label="Estimated token limit" type="number" min="1" value={limitTokens} onChange={(event) => setLimitTokens(event.target.value)} /><button className="button-secondary" disabled={saving}>{saving ? "Saving…" : "Set hard limit"}</button></form>{budget.policies.map((item) => <p key={item.period} className={`mt-2 text-xs ${item.blocked ? "text-danger" : item.warn ? "text-warning" : "text-text-tertiary"}`}>{item.period}: {item.used_tokens}/{item.limit_tokens} estimated tokens{item.blocked ? " · requests stopped" : ""}</p>)}</article>
        <article className="panel p-4 sm:p-5"><h3 className="text-[15px] font-medium">Provider routing</h3><p className="mt-2 text-xs leading-5 text-text-secondary">Fallback preserves authorized workspace context only. Any tool action stays on the selected provider and requires a new confirmation.</p><form className="mt-4 grid gap-3" onSubmit={saveRouting}><label className="text-xs font-medium text-text-secondary">Policy<select className="field mt-1.5 w-full" value={routing.policy} onChange={(event) => setRouting((current) => ({ ...current, policy: event.target.value as Routing["policy"] }))}><option value="STRICT_PROVIDER">Strict provider</option><option value="FALLBACK_ALLOWED">Fallback allowed</option><option value="ASK_BEFORE_FALLBACK">Ask before fallback</option></select></label>{routing.policy !== "STRICT_PROVIDER" && <div className="grid gap-2 sm:grid-cols-2"><label className="text-xs font-medium text-text-secondary">Fallback service<select className="field mt-1.5 w-full" value={routing.fallback_provider || ""} onChange={(event) => { const next = configured.find((item) => item.id === event.target.value); setRouting((current) => ({ ...current, fallback_provider: event.target.value || undefined, fallback_model: next?.models[0] })); }}><option value="">Choose service</option>{configured.map((item) => <option key={item.id} value={item.id}>{item.id}</option>)}</select></label><label className="text-xs font-medium text-text-secondary">Fallback model<select className="field mt-1.5 w-full" value={routing.fallback_model || ""} onChange={(event) => setRouting((current) => ({ ...current, fallback_model: event.target.value || undefined }))}><option value="">Choose model</option>{configured.find((item) => item.id === routing.fallback_provider)?.models.map((model) => <option key={model} value={model}>{model}</option>)}</select></label></div>}<button className="button-secondary" disabled={saving}>{saving ? "Saving…" : "Save routing"}</button></form></article>
        <article className="panel p-4 sm:p-5 lg:col-span-2"><div className="flex items-center gap-2"><DatabaseBackup aria-hidden size={17} className="text-text-tertiary" /><h3 className="text-[15px] font-medium">Backup, restore & diagnostics</h3></div><p className="mt-2 text-sm leading-6 text-text-secondary">Before a restore or update, create a verified data backup. Backup archives never include provider credentials. Doctor reports database integrity, migration status, safe configuration booleans, and recovery metadata counts without exposing their contents.</p><div className="mt-3 flex flex-wrap gap-3"><a className="button-quiet px-0 text-accent-hover" href="https://github.com/sui-ni2/personal-ai-os/blob/main/docs/transfer-and-backup.md">Backup & restore guide</a><a className="button-quiet px-0 text-accent-hover" href="https://github.com/sui-ni2/personal-ai-os/blob/main/docs/windows-distribution.md">Windows update & rollback</a><button type="button" className="button-quiet px-0 text-accent-hover" onClick={() => void downloadDoctorReport()} disabled={lifecycleBusy}><HeartPulse aria-hidden size={15} />Download safe Doctor report</button><span className="text-xs text-text-tertiary">Windows signing, Docker, physical devices, and screen readers remain separate external checks.</span></div></article>
      </div>
      {saved && <p className="flex items-center gap-2 text-sm text-success" role="status"><Check aria-hidden size={15} />{saved}</p>}
      {lifecycleNotice && <p className="flex items-center gap-2 text-sm text-text-secondary" role="status"><Check aria-hidden size={15} />{lifecycleNotice}</p>}
      <p className="flex items-center gap-2 text-xs text-text-tertiary"><AlertTriangle aria-hidden size={14} />Advanced connector, repository and execution-trace controls remain in Advanced mode.</p>
    </section>
  );
}
