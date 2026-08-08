"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiJson } from "@/lib/api";

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
  mcp: {
    servers: { id: string; configured: boolean }[];
    connectors: MCPConnector[];
    stdio_command_aliases: string[];
  };
  secrets: { storage: string; values_exposed: boolean };
};

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
  const [discovered, setDiscovered] = useState<Record<string, DiscoveredTool[]>>({});

  async function load() {
    const item = await apiJson<Settings>("/api/settings");
    setSettings(item);
    setProvider(item.default_provider);
    setModel(item.default_model);
    if (!command && item.mcp.stdio_command_aliases.length) {
      setCommand(item.mcp.stdio_command_aliases[0]);
    }
  }

  useEffect(() => { void load(); }, []);
  const selected = useMemo(
    () => settings?.providers.find((item) => item.id === provider),
    [provider, settings],
  );

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
    } catch (error) {
      setConnectorError(error instanceof Error ? error.message : "Connector creation failed");
    }
  }

  async function toggleConnector(connector: MCPConnector) {
    await apiJson(`/api/mcp/connectors/${connector.id}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled: !connector.enabled }),
    });
    await load();
  }

  async function discoverConnector(connector: MCPConnector) {
    setConnectorError("");
    try {
      const result = await apiJson<{ tools: DiscoveredTool[] }>(
        `/api/mcp/connectors/${connector.id}/discover`,
        { method: "POST" },
      );
      setDiscovered((current) => ({ ...current, [connector.id]: result.tools }));
      await load();
    } catch (error) {
      setConnectorError(error instanceof Error ? error.message : "Tool discovery failed");
      await load();
    }
  }

  async function toggleAllowedTool(connector: MCPConnector, toolName: string) {
    const next = connector.allowed_tools.includes(toolName)
      ? connector.allowed_tools.filter((item) => item !== toolName)
      : [...connector.allowed_tools, toolName];
    await apiJson(`/api/mcp/connectors/${connector.id}`, {
      method: "PATCH",
      body: JSON.stringify({ allowed_tools: next }),
    });
    await load();
  }

  if (!settings) return <div className="panel p-8 text-sm text-muted">Loading safe configuration...</div>;
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <form onSubmit={submitDefaults} className="panel p-6">
          <p className="eyebrow">Model routing</p><h2 className="mt-2 text-2xl font-semibold">Defaults</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <label className="text-xs font-semibold text-muted">Provider
              <select className="field mt-2 w-full" value={provider} onChange={(event) => { const id = event.target.value; setProvider(id); setModel(settings.providers.find((item) => item.id === id)?.models[0] || ""); }}>
                {settings.providers.map((item) => <option key={item.id} value={item.id}>{item.id}</option>)}
              </select>
            </label>
            <label className="text-xs font-semibold text-muted">Model
              <select className="field mt-2 w-full" value={model} onChange={(event) => setModel(event.target.value)}>
                {(selected?.models || []).map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
          </div>
          <button className="button-primary mt-5">{saved ? "Saved" : "Save defaults"}</button>
        </form>
        <section className="panel p-6">
          <p className="eyebrow">Security</p>
          <p className="mt-3 text-sm leading-6 text-muted">Secrets are read from {settings.secrets.storage}. Values exposed to the browser: <strong>{String(settings.secrets.values_exposed)}</strong>.</p>
          <div className="mt-4 rounded-2xl bg-black/[0.025] p-4 text-sm"><span className="mr-2 inline-block size-2 rounded-full bg-emerald-500" />Built-in MCP {settings.mcp.servers[0]?.id} connected</div>
        </section>
      </div>

      <section className="panel p-6">
        <p className="eyebrow">MCP connectors</p>
        <div className="mt-2 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div><h2 className="text-2xl font-semibold">External transports</h2><p className="mt-2 text-sm leading-6 text-muted">HTTP endpoints are fixed configuration. stdio uses server-side command aliases only; no shell string is accepted.</p></div>
          <span className="text-sm text-muted">{settings.mcp.connectors.length} configured</span>
        </div>
        <form onSubmit={createConnector} className="mt-6 grid gap-3 rounded-3xl bg-black/[0.025] p-4 md:grid-cols-2 xl:grid-cols-5">
          <input className="field" placeholder="Connector name" value={connectorName} onChange={(event) => setConnectorName(event.target.value)} required />
          <select className="field" value={transport} onChange={(event) => setTransport(event.target.value as "http" | "stdio")}><option value="http">HTTP</option><option value="stdio">stdio</option></select>
          {transport === "http" ? (
            <input className="field xl:col-span-2" placeholder="https://server.example/mcp" value={endpoint} onChange={(event) => setEndpoint(event.target.value)} required />
          ) : (
            <select className="field xl:col-span-2" value={command} onChange={(event) => setCommand(event.target.value)} required>
              <option value="">Choose allowlisted command</option>
              {settings.mcp.stdio_command_aliases.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          )}
          <input className="field" placeholder="Allowed tools, comma separated" value={allowedTools} onChange={(event) => setAllowedTools(event.target.value)} />
          <button className="button-primary md:col-span-2 xl:col-span-5" disabled={transport === "stdio" && !command}>Add connector</button>
        </form>
        {connectorError && <p className="mt-4 rounded-2xl bg-red-50 p-4 text-sm text-red-800">{connectorError}</p>}
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {settings.mcp.connectors.map((connector) => (
            <article key={connector.id} className="rounded-3xl border border-black/5 bg-white/55 p-5">
              <div className="flex items-start justify-between gap-4">
                <div><p className="eyebrow">{connector.transport} · {connector.connection_status}</p><h3 className="mt-2 text-xl font-semibold">{connector.name}</h3><p className="mt-2 break-all text-xs text-muted">{connector.endpoint || `command alias: ${connector.command}`}</p></div>
                <button className="min-h-11 rounded-2xl border border-black/10 px-4 text-xs font-semibold" onClick={() => void toggleConnector(connector)}>{connector.enabled ? "Disable" : "Enable"}</button>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button className="button-primary" onClick={() => void discoverConnector(connector)} disabled={!connector.enabled}>Discover tools</button>
                {connector.allowed_tools.map((item) => <span key={item} className="rounded-full bg-emerald-100 px-3 py-2 text-xs font-semibold text-emerald-800">allowed: {item}</span>)}
              </div>
              {(discovered[connector.id] || []).length > 0 && (
                <div className="mt-4 space-y-2 rounded-2xl bg-black/[0.025] p-3">
                  {(discovered[connector.id] || []).map((tool) => (
                    <button key={tool.name} className="flex min-h-11 w-full items-center justify-between rounded-xl bg-white/70 px-3 text-left text-xs" onClick={() => void toggleAllowedTool(connector, tool.name)}>
                      <span><strong>{tool.name}</strong><span className="ml-2 text-muted">{tool.description}</span></span>
                      <span>{connector.allowed_tools.includes(tool.name) ? "Remove" : "Allow"}</span>
                    </button>
                  ))}
                </div>
              )}
              <p className="mt-4 text-xs leading-5 text-muted">Last seen: {connector.last_seen ? new Date(connector.last_seen).toLocaleString() : "never"}{connector.last_error ? ` · Last error: ${connector.last_error}` : ""}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
