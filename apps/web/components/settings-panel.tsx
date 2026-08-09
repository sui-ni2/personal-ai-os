"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Cable, Check, ChevronDown, Database, Mic2, Palette, Plus, RefreshCw, Server, ShieldCheck, Smartphone } from "lucide-react";
import { apiJson } from "@/lib/api";
import { ErrorState, LoadingState } from "@/components/ui-states";

type Provider = { id: string; configured: boolean; models: string[] };
type MCPConnector = {
  id: string;
  name: string;
  transport: "http" | "stdio";
  endpoint?: string;
  command?: string;
  enabled: boolean;
  allowed_tools: string[];
  connection_status: "disabled" | "configured" | "connected" | "error";
  last_error?: string;
  last_seen?: string;
  timeout_seconds: number;
};
type DiscoveredTool = { name: string; description: string; input_schema: Record<string, unknown> };
type Settings = {
  default_provider: string;
  default_model: string;
  providers: Provider[];
  mcp: { servers: { id: string; configured: boolean }[]; connectors: MCPConnector[]; stdio_command_aliases: string[] };
  secrets: { storage: string; values_exposed: boolean };
};
type MobileReadiness = { secure: boolean; https: boolean; standalone: boolean; microphone: boolean };
type RealtimeStatus = { configured: boolean; provider: "openai" | "compatible"; model: string; transport: "webrtc" };

function providerName(id: string) {
  if (id === "openai") return "OpenAI";
  if (id === "anthropic") return "Anthropic";
  return id.charAt(0).toUpperCase() + id.slice(1);
}

export function SettingsPanel() {
  const [settings, setSettings] = useState<Settings>();
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [saved, setSaved] = useState(false);
  const [connectorName, setConnectorName] = useState("");
  const [transport, setTransport] = useState<"http" | "stdio">("http");
  const [endpoint, setEndpoint] = useState("");
  const [command, setCommand] = useState("");
  const [allowedTools, setAllowedTools] = useState("");
  const [connectorError, setConnectorError] = useState("");
  const [loadError, setLoadError] = useState(false);
  const [discovered, setDiscovered] = useState<Record<string, DiscoveredTool[]>>({});
  const [mobileReadiness, setMobileReadiness] = useState<MobileReadiness>();
  const [realtime, setRealtime] = useState<RealtimeStatus>();

  async function load() {
    try {
      const [item, realtimeStatus] = await Promise.all([
        apiJson<Settings>("/api/settings"),
        apiJson<RealtimeStatus>("/api/realtime/status"),
      ]);
      setSettings(item);
      setRealtime(realtimeStatus);
      setProvider(item.default_provider);
      setModel(item.default_model);
      if (!command && item.mcp.stdio_command_aliases.length) setCommand(item.mcp.stdio_command_aliases[0]);
      setLoadError(false);
    } catch {
      setLoadError(true);
    }
  }

  useEffect(() => { void load(); }, []);
  useEffect(() => {
    const device = window.navigator as Navigator & { standalone?: boolean };
    setMobileReadiness({
      secure: window.isSecureContext,
      https: window.location.protocol === "https:",
      standalone: Boolean(device.standalone) || window.matchMedia("(display-mode: standalone)").matches,
      microphone: Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia),
    });
  }, []);
  const selected = useMemo(() => settings?.providers.find((item) => item.id === provider), [provider, settings]);

  async function submitDefaults(event: FormEvent) {
    event.preventDefault();
    const item = await apiJson<Settings>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify({ default_provider: provider, default_model: model }),
    });
    setSettings(item);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  }

  async function createConnector(event: FormEvent) {
    event.preventDefault();
    setConnectorError("");
    try {
      await apiJson("/api/mcp/connectors", {
        method: "POST",
        body: JSON.stringify({
          name: connectorName,
          transport,
          endpoint: transport === "http" ? endpoint : null,
          command: transport === "stdio" ? command : null,
          enabled: true,
          allowed_tools: allowedTools.split(",").map((item) => item.trim()).filter(Boolean),
          timeout_seconds: 15,
        }),
      });
      setConnectorName("");
      setEndpoint("");
      setAllowedTools("");
      await load();
    } catch {
      setConnectorError("The connector could not be added. Check the configuration and try again.");
    }
  }

  async function toggleConnector(connector: MCPConnector) {
    await apiJson(`/api/mcp/connectors/${connector.id}`, { method: "PATCH", body: JSON.stringify({ enabled: !connector.enabled }) });
    await load();
  }

  async function discoverConnector(connector: MCPConnector) {
    setConnectorError("");
    try {
      const result = await apiJson<{ tools: DiscoveredTool[] }>(`/api/mcp/connectors/${connector.id}/discover`, { method: "POST" });
      setDiscovered((current) => ({ ...current, [connector.id]: result.tools }));
      await load();
    } catch {
      setConnectorError("Tool discovery failed. Check that the connector is enabled and reachable.");
      await load();
    }
  }

  async function toggleAllowedTool(connector: MCPConnector, toolName: string) {
    const next = connector.allowed_tools.includes(toolName)
      ? connector.allowed_tools.filter((item) => item !== toolName)
      : [...connector.allowed_tools, toolName];
    await apiJson(`/api/mcp/connectors/${connector.id}`, { method: "PATCH", body: JSON.stringify({ allowed_tools: next }) });
    await load();
  }

  if (loadError) return <ErrorState title="Settings are unavailable" detail="Safe configuration could not be loaded. Start the API and refresh this page." />;
  if (!settings) return <LoadingState label="Loading safe configuration" />;

  return (
    <div className="space-y-8 sm:space-y-10">
      <nav className="scrollbar-subtle -mx-1 flex gap-2 overflow-x-auto px-1 pb-1" aria-label="Settings sections">
        {[{ href: "#models-settings", label: "Models" }, { href: "#mcp-settings", label: "MCP" }, { href: "#appearance-settings", label: "Appearance" }, { href: "#data-settings", label: "Data" }].map((item) => <a key={item.href} href={item.href} className="chip min-h-11 shrink-0 hover:bg-accent-soft hover:text-accent-hover">{item.label}</a>)}
      </nav>
      <section className="scroll-mt-6" aria-labelledby="models-settings">
        <div className="mb-4 flex items-center gap-2"><Server aria-hidden size={18} className="text-text-tertiary" /><h2 id="models-settings" className="section-title">Models</h2></div>
        <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <div className="grid gap-3 sm:grid-cols-2">
            {settings.providers.map((item) => (
              <article key={item.id} className="panel p-4 sm:p-5">
                <div className="flex items-center justify-between gap-4">
                  <h3 className="text-[15px] font-medium">{providerName(item.id)}</h3>
                  <span className={`chip ${item.configured ? "bg-success/10 text-success" : ""}`}><span className={`status-dot ${item.configured ? "bg-success" : "bg-warning"}`} />{item.configured ? "Configured" : "Not configured"}</span>
                </div>
                <p className="mt-3 text-sm leading-6 text-text-secondary">{item.models.length} {item.models.length === 1 ? "model" : "models"} available from provider configuration.</p>
              </article>
            ))}
          </div>
          <form onSubmit={submitDefaults} className="panel p-4 sm:p-5">
            <h3 className="text-[15px] font-medium">Default model</h3>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              <label className="text-xs font-medium text-text-secondary">Provider
                <select className="field mt-1.5 w-full" value={provider} onChange={(event) => { const id = event.target.value; setProvider(id); setModel(settings.providers.find((item) => item.id === id)?.models[0] || ""); }}>
                  {settings.providers.map((item) => <option key={item.id} value={item.id}>{providerName(item.id)}</option>)}
                </select>
              </label>
              <label className="text-xs font-medium text-text-secondary">Model
                <select className="field mt-1.5 w-full" value={model} onChange={(event) => setModel(event.target.value)}>
                  {(selected?.models || []).map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
            </div>
            <button className="button-primary mt-4 w-full">{saved ? <><Check aria-hidden size={17} />Saved</> : "Save default"}</button>
            <p className="sr-only" role="status" aria-live="polite">{saved ? "Default model saved." : ""}</p>
          </form>
        </div>
      </section>

      <section className="scroll-mt-6" aria-labelledby="mcp-settings">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <div className="flex items-center gap-2"><Cable aria-hidden size={18} className="text-text-tertiary" /><h2 id="mcp-settings" className="section-title">MCP</h2></div>
            <p className="mt-2 text-sm leading-6 text-text-secondary">Allowlisted tool connections available to your workspace.</p>
          </div>
          <details className="group relative">
            <summary className="button-primary cursor-pointer list-none"><Plus aria-hidden size={17} />Add connector</summary>
            <form onSubmit={createConnector} className="panel-elevated mt-2 grid gap-3 p-4 sm:absolute sm:right-0 sm:z-20 sm:w-[520px] sm:grid-cols-2">
              <input className="field" aria-label="Connector name" placeholder="Connector name" value={connectorName} onChange={(event) => setConnectorName(event.target.value)} required />
              <select className="field" aria-label="Connector transport" value={transport} onChange={(event) => setTransport(event.target.value as "http" | "stdio")}><option value="http">HTTP</option><option value="stdio">stdio</option></select>
              {transport === "http" ? (
                <input className="field sm:col-span-2" aria-label="Connector HTTP endpoint" placeholder="https://server.example/mcp" value={endpoint} onChange={(event) => setEndpoint(event.target.value)} required />
              ) : (
                <select className="field sm:col-span-2" aria-label="Connector command alias" value={command} onChange={(event) => setCommand(event.target.value)} required>
                  <option value="">Choose allowlisted command</option>
                  {settings.mcp.stdio_command_aliases.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              )}
              <input className="field sm:col-span-2" aria-label="Allowed tools" placeholder="Allowed tools, comma separated" value={allowedTools} onChange={(event) => setAllowedTools(event.target.value)} />
              <button className="button-primary sm:col-span-2" disabled={transport === "stdio" && !command}>Add connector</button>
            </form>
          </details>
        </div>
        {connectorError && <div className="mt-4"><ErrorState title="Connection needs attention" detail={connectorError} /></div>}
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {settings.mcp.connectors.length === 0 && (
            <div className="panel col-span-full flex items-center gap-3 p-5 text-sm text-text-secondary"><ShieldCheck aria-hidden size={18} className="text-success" />No external connectors configured. The built-in allowlisted reference tool remains available.</div>
          )}
          {settings.mcp.connectors.map((connector) => (
            <article key={connector.id} className="panel p-4 sm:p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2"><h3 className="text-[15px] font-medium">{connector.name}</h3><span className="chip uppercase">{connector.transport}</span></div>
                  <p className="mt-2 text-sm text-text-secondary">{connector.connection_status === "error" ? "Connection error" : connector.connection_status.charAt(0).toUpperCase() + connector.connection_status.slice(1)}</p>
                </div>
                <button className="button-secondary px-3 text-xs" onClick={() => void toggleConnector(connector)}>{connector.enabled ? "Disable" : "Enable"}</button>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button className="button-quiet px-2 text-xs" onClick={() => void discoverConnector(connector)} disabled={!connector.enabled}><RefreshCw aria-hidden size={14} />Discover tools</button>
                <span className="chip">{connector.allowed_tools.length} allowed</span>
              </div>
              {(discovered[connector.id] || []).length > 0 && (
                <div className="mt-4 space-y-1 rounded-control bg-surface-subtle p-2">
                  {(discovered[connector.id] || []).map((tool) => (
                    <button key={tool.name} className="flex min-h-11 w-full items-center justify-between gap-3 rounded-small bg-surface px-3 text-left text-xs" onClick={() => void toggleAllowedTool(connector, tool.name)}>
                      <span className="min-w-0"><strong className="block truncate font-medium">{tool.name}</strong><span className="mt-0.5 block truncate text-text-tertiary">{tool.description}</span></span>
                      <span className="shrink-0 text-accent-hover">{connector.allowed_tools.includes(tool.name) ? "Remove" : "Allow"}</span>
                    </button>
                  ))}
                </div>
              )}
              <details className="group mt-4 border-t border-line pt-3">
                <summary className="flex cursor-pointer list-none items-center gap-2 text-xs font-medium text-text-tertiary">Advanced details <ChevronDown aria-hidden size={14} className="transition-transform group-open:rotate-180" /></summary>
                <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 rounded-small bg-surface-subtle p-3 text-xs text-text-secondary">
                  <dt>Target</dt><dd className="truncate font-mono">{connector.endpoint || `command alias: ${connector.command}`}</dd>
                  <dt>Last seen</dt><dd>{connector.last_seen ? new Date(connector.last_seen).toLocaleString() : "Never"}</dd>
                  <dt>Status</dt><dd>{connector.last_error ? "Last attempt failed" : connector.connection_status}</dd>
                </dl>
              </details>
            </article>
          ))}
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2">
        <section className="panel scroll-mt-6 p-4 sm:p-5" aria-labelledby="appearance-settings">
          <div className="flex items-center gap-2"><Palette aria-hidden size={18} className="text-text-tertiary" /><h2 id="appearance-settings" className="section-title">Appearance</h2></div>
          <div className="mt-5 flex items-center justify-between rounded-control bg-surface-subtle p-4"><span className="text-sm font-medium">Theme</span><span className="chip">Light</span></div>
        </section>
        <section className="panel scroll-mt-6 p-4 sm:p-5" aria-labelledby="data-settings">
          <div className="flex items-center gap-2"><Database aria-hidden size={18} className="text-text-tertiary" /><h2 id="data-settings" className="section-title">Data</h2></div>
          <div className="mt-5 flex gap-3 rounded-control bg-surface-subtle p-4"><ShieldCheck aria-hidden size={18} className="mt-0.5 shrink-0 text-success" /><div><p className="text-sm font-medium">Local persistence</p><p className="mt-1 text-xs leading-5 text-text-secondary">Conversation, memory, and repository data remain managed by the local API. Secret values are never exposed here.</p></div></div>
        </section>
        <section className="panel scroll-mt-6 p-4 sm:col-span-2 sm:p-5" aria-labelledby="mobile-settings">
          <div className="flex items-center gap-2"><Smartphone aria-hidden size={18} className="text-text-tertiary" /><h2 id="mobile-settings" className="section-title">Mobile app</h2></div>
          <p className="mt-2 text-sm leading-6 text-text-secondary">Installation and GPT Live depend on the way this address is opened on your phone.</p>
          <dl className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-control bg-surface-subtle p-4">
              <dt className="text-xs font-medium text-text-tertiary">Connection</dt>
              <dd className="mt-2 flex items-center gap-2 text-sm font-medium"><ShieldCheck aria-hidden size={16} className={!mobileReadiness ? "text-text-tertiary" : mobileReadiness.secure ? "text-success" : "text-warning"} />{!mobileReadiness ? "Checking…" : mobileReadiness.https ? "Secure HTTPS" : mobileReadiness.secure ? "Local secure context" : "HTTPS required"}</dd>
            </div>
            <div className="rounded-control bg-surface-subtle p-4">
              <dt className="text-xs font-medium text-text-tertiary">App mode</dt>
              <dd className="mt-2 flex items-center gap-2 text-sm font-medium"><Smartphone aria-hidden size={16} className={mobileReadiness?.standalone ? "text-success" : "text-text-tertiary"} />{!mobileReadiness ? "Checking…" : mobileReadiness.standalone ? "Installed" : "Browser"}</dd>
            </div>
            <div className="rounded-control bg-surface-subtle p-4">
              <dt className="text-xs font-medium text-text-tertiary">Media capture</dt>
              <dd className="mt-2 flex items-center gap-2 text-sm font-medium"><Mic2 aria-hidden size={16} className={!mobileReadiness ? "text-text-tertiary" : mobileReadiness.microphone ? "text-success" : "text-warning"} />{!mobileReadiness ? "Checking…" : mobileReadiness.microphone ? "Browser ready" : "Unavailable"}</dd>
            </div>
            <div className="rounded-control bg-surface-subtle p-4">
              <dt className="text-xs font-medium text-text-tertiary">GPT Live</dt>
              <dd className="mt-2 flex items-center gap-2 text-sm font-medium"><Server aria-hidden size={16} className={!realtime ? "text-text-tertiary" : realtime.configured ? "text-success" : "text-warning"} />{!realtime ? "Checking…" : realtime.configured ? "Ready" : "Credential required"}</dd>
            </div>
          </dl>
          <p className="mt-4 text-xs leading-5 text-text-tertiary">Use More → Install app when offered. On iPhone, open this HTTPS address in Safari and choose Add to Home Screen.</p>
        </section>
      </div>
    </div>
  );
}
