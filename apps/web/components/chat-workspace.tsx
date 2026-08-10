"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  BookmarkPlus,
  Check,
  ChevronDown,
  ClipboardList,
  Lightbulb,
  History,
  ListChecks,
  MessageCircle,
  Mic2,
  MoreHorizontal,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  Square,
  Wrench,
  X,
} from "lucide-react";
import { ActivityPanel } from "@/components/activity-panel";
import { ModelSelector, type ProviderOption } from "@/components/model-selector";
import { RichMessage } from "@/components/rich-message";
import { ErrorState } from "@/components/ui-states";
import { apiJson, type SseEvent, streamSse } from "@/lib/api";
import { focusableSelector, trapFocus } from "@/lib/focus";

type Project = { id: string; name: string; description: string };
type Conversation = { id: string; title: string; provider: string; model: string; project_id?: string; created_at: string; updated_at: string };
type PersistedMessage = { id: string; role: "user" | "assistant" | "system" | "tool"; content: string };
type UiMessage = { id?: string; role: "user" | "assistant" | "system"; content: string };
type ConversationDetail = { conversation: Conversation; messages: PersistedMessage[]; execution_events: SseEvent[] };
type MCPConnector = { id: string; name: string; enabled: boolean; allowed_tools: string[]; connection_status: "disabled" | "configured" | "connected" | "error" };
type RealtimeStatus = { configured: boolean; provider: "openai" | "compatible"; model: string; transcription_model: string; transport: "webrtc" };
type LiveState = "idle" | "connecting" | "listening" | "error";
type MemoryKind = "fact" | "preference" | "rule" | "project";
type MemoryTarget = UiMessage & { index: number };

const ACTIVE_CONVERSATION_KEY = "personal-ai-os.active-conversation";
const mobilePreview = process.env.NEXT_PUBLIC_PERSONAL_AI_OS_MOBILE_PREVIEW === "true";
const starterPrompts = [
  { label: "Help me plan today", prompt: "Help me plan today", Icon: ClipboardList },
  { label: "Think through a decision", prompt: "Help me think through a decision", Icon: Lightbulb },
  { label: "Turn an idea into next steps", prompt: "Turn my idea into clear next steps", Icon: ListChecks },
];

export function ChatWorkspace() {
  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [connectors, setConnectors] = useState<MCPConnector[]>([]);
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("");
  const [project, setProject] = useState("general");
  const [projectFilter, setProjectFilter] = useState("all");
  const [conversationId, setConversationId] = useState<string>();
  const [input, setInput] = useState("");
  const [useMcp, setUseMcp] = useState(false);
  const [connectorId, setConnectorId] = useState("local-reference");
  const [toolName, setToolName] = useState("system.echo");
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [trace, setTrace] = useState<SseEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [apiError, setApiError] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [mode, setMode] = useState<"text" | "live">("text");
  const [realtime, setRealtime] = useState<RealtimeStatus>();
  const [liveState, setLiveState] = useState<LiveState>("idle");
  const [liveMessage, setLiveMessage] = useState("Tap start when you are ready. Microphone access is requested only then.");
  const [liveCaption, setLiveCaption] = useState("");
  const [liveSaveWarning, setLiveSaveWarning] = useState("");
  const [livePlaybackBlocked, setLivePlaybackBlocked] = useState(false);
  const [memoryTarget, setMemoryTarget] = useState<MemoryTarget>();
  const [memoryKind, setMemoryKind] = useState<MemoryKind>("fact");
  const [memoryText, setMemoryText] = useState("");
  const [memoryState, setMemoryState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const conversationRef = useRef<HTMLDivElement>(null);
  const historyDialogRef = useRef<HTMLElement>(null);
  const historyTriggerRef = useRef<HTMLButtonElement>(null);
  const memoryDialogRef = useRef<HTMLElement>(null);
  const memoryReturnFocusRef = useRef<HTMLElement | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const inputTranscriptRef = useRef("");
  const outputTranscriptRef = useRef("");
  const savedLiveItemsRef = useRef(new Set<string>());
  const liveDisconnectTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams(window.location.search);
    const requestedMode = params.get("mode") === "live" ? "live" : "text";
    setMode(requestedMode);
    void Promise.all([
      apiJson<{ items: ProviderOption[] }>("/api/providers"),
      apiJson<{ items: Project[] }>("/api/projects"),
      apiJson<{ default_provider: string; default_model: string }>("/api/settings"),
      apiJson<{ items: Conversation[] }>("/api/conversations"),
      apiJson<{ items: MCPConnector[] }>("/api/mcp/connectors"),
      apiJson<RealtimeStatus>("/api/realtime/status"),
    ])
      .then(async ([providerData, projectData, settings, conversationData, connectorData, realtimeData]) => {
        if (cancelled) return;
        setProviders(providerData.items);
        setProjects(projectData.items);
        setProvider(settings.default_provider);
        setModel(settings.default_model);
        setConversations(conversationData.items);
        setConnectors(connectorData.items);
        setRealtime(realtimeData);
        const requestedProject = params.get("project");
        if (requestedProject && projectData.items.some((item) => item.id === requestedProject)) setProject(requestedProject);
        if (params.get("new") === "1") {
          window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
          return;
        }
        const savedId = window.localStorage.getItem(ACTIVE_CONVERSATION_KEY);
        if (savedId) {
          try { await openConversation(savedId); } catch { window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY); }
        }
      })
      .catch(() => {
        if (!mobilePreview) {
          setApiError(true);
          return;
        }
        setProviders([
          { id: "openai", configured: false, models: ["gpt-5.1", "gpt-4.1-mini"] },
          { id: "anthropic", configured: false, models: ["claude-sonnet-4-5"] },
        ]);
        setProjects([
          { id: "general", name: "General", description: "Everyday thinking and planning" },
          { id: "p5", name: "P5 Lab", description: "Paper-only research workspace" },
        ]);
        setModel("gpt-5.1");
        setRealtime({
          configured: false,
          provider: "openai",
          model: "gpt-realtime-2.1",
          transcription_model: "gpt-realtime-whisper",
          transport: "webrtc",
        });
      });
    return () => { cancelled = true; stopLive(false); };
  }, []);

  useEffect(() => { conversationRef.current?.scrollTo({ top: conversationRef.current.scrollHeight, behavior: running ? "auto" : "smooth" }); }, [messages, running]);

  useEffect(() => {
    if (!memoryTarget) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => memoryDialogRef.current?.querySelector<HTMLElement>("textarea")?.focus());
    return () => { document.body.style.overflow = previous; };
  }, [memoryTarget]);

  useEffect(() => {
    if (!historyOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => historyDialogRef.current?.querySelector<HTMLElement>(focusableSelector)?.focus());
    return () => { document.body.style.overflow = previous; };
  }, [historyOpen]);

  const selectedConnector = useMemo(() => connectors.find((item) => item.id === connectorId), [connectorId, connectors]);
  const selectedProvider = useMemo(() => providers.find((item) => item.id === provider), [provider, providers]);
  const providerReady = Boolean(selectedProvider?.configured);
  const activeConversation = useMemo(() => conversations.find((item) => item.id === conversationId), [conversationId, conversations]);
  const title = activeConversation?.title || "New conversation";

  function selectConnector(id: string) {
    setConnectorId(id);
    const connector = connectors.find((item) => item.id === id);
    setToolName(id === "local-reference" ? "system.echo" : connector?.allowed_tools[0] || "");
  }

  async function loadConversations(filter = projectFilter) {
    const query = filter === "all" ? "" : `?project_id=${encodeURIComponent(filter)}`;
    const data = await apiJson<{ items: Conversation[] }>(`/api/conversations${query}`);
    setConversations(data.items);
    return data.items;
  }

  async function openConversation(id: string) {
    setLoadingConversation(true);
    try {
      const detail = await apiJson<ConversationDetail>(`/api/conversations/${id}`);
      setConversationId(detail.conversation.id);
      setProvider(detail.conversation.provider);
      setModel(detail.conversation.model);
      setProject(detail.conversation.project_id || "general");
      setMessages(detail.messages.map((item) => ({ id: item.id, role: item.role === "user" || item.role === "assistant" ? item.role : "system", content: item.content })));
      setTrace(detail.execution_events);
      if (historyOpen) closeHistory();
      else setHistoryOpen(false);
      window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, detail.conversation.id);
    } finally { setLoadingConversation(false); }
  }

  async function createConversation() {
    if (!model || running) return undefined;
    const created = await apiJson<Conversation>("/api/conversations", { method: "POST", body: JSON.stringify({ provider, model, project_id: project, title: "New conversation" }) });
    setConversationId(created.id);
    setMessages([]);
    setTrace([]);
    window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, created.id);
    await loadConversations();
    return created.id;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || !model || running) return;
    setMessages((current) => [...current, { role: "user", content }, { role: "assistant", content: "" }]);
    setInput("");
    setRunning(true);
    try {
      await streamSse("/api/chat/stream", {
        conversation_id: conversationId, provider, model, project_id: project, content,
        tool: useMcp ? { name: toolName, connector_id: connectorId === "local-reference" ? null : connectorId, arguments: { message: content } } : null,
      }, (item) => {
        setTrace((current) => [...current, item]);
        if (item.type === "message") {
          const delta = String(item.payload.delta || "");
          setMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, content: message.content + delta } : message));
        }
        if (item.type === "error") setMessages((current) => current.map((message, index) => index === current.length - 1 ? { role: "system", content: "The request could not be completed. Check your provider or tool settings, then try again." } : message));
        if (item.type === "done" && typeof item.payload.conversation_id === "string") {
          setConversationId(item.payload.conversation_id);
          window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, item.payload.conversation_id);
        }
      });
      await loadConversations();
    } catch {
      setMessages((current) => current.map((message, index) => index === current.length - 1 ? { role: "system", content: "The connection ended before the response completed. Check the service and try again." } : message));
    } finally { setRunning(false); }
  }

  function stopLive(update = true) {
    if (liveDisconnectTimerRef.current !== null) {
      window.clearTimeout(liveDisconnectTimerRef.current);
      liveDisconnectTimerRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    peerRef.current?.close();
    peerRef.current = null;
    if (audioRef.current) { audioRef.current.srcObject = null; audioRef.current.remove(); audioRef.current = null; }
    setLivePlaybackBlocked(false);
    if (update) { setLiveState("idle"); setLiveMessage("Live conversation ended. Tap start whenever you want to continue."); }
  }

  async function resumeLiveAudio() {
    if (!audioRef.current) return;
    try {
      await audioRef.current.play();
      setLivePlaybackBlocked(false);
      setLiveMessage("Listening — speak naturally. You can interrupt at any time.");
    } catch {
      setLiveMessage("Audio is still paused by the browser. Check media permission and try again.");
    }
  }

  async function persistLiveTranscript(
    activeId: string,
    role: "user" | "assistant",
    content: string,
    eventKey: string,
  ) {
    const normalized = content.trim();
    if (!normalized || savedLiveItemsRef.current.has(eventKey)) return;
    savedLiveItemsRef.current.add(eventKey);
    try {
      const saved = await apiJson<{ message: PersistedMessage; conversation: Conversation }>(
        `/api/conversations/${activeId}/realtime-transcript`,
        { method: "POST", body: JSON.stringify({ role, content: normalized }) },
      );
      setMessages((current) => [...current, { id: saved.message.id, role, content: normalized }]);
      setConversations((current) => {
        const exists = current.some((item) => item.id === saved.conversation.id);
        return exists
          ? current.map((item) => item.id === saved.conversation.id ? saved.conversation : item)
          : [saved.conversation, ...current];
      });
    } catch {
      savedLiveItemsRef.current.delete(eventKey);
      setLiveSaveWarning("Live is still connected, but this completed transcript could not be saved.");
    }
  }

  async function startLive() {
    if (!realtime?.configured) {
      setLiveState("error");
      setLiveMessage("GPT Live is not configured. Add a server-side Realtime credential, then try again.");
      return;
    }
    if (!window.isSecureContext) {
      setLiveState("error");
      setLiveMessage("GPT Live needs a secure HTTPS connection on a phone. Reopen this app from its HTTPS address, then try again.");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setLiveState("error");
      setLiveMessage("This browser does not provide microphone access for GPT Live.");
      return;
    }
    setLiveState("connecting");
    setLiveMessage("Requesting microphone access…");
    setLiveCaption("");
    setLiveSaveWarning("");
    setLivePlaybackBlocked(false);
    inputTranscriptRef.current = "";
    outputTranscriptRef.current = "";
    savedLiveItemsRef.current.clear();
    try {
      const activeId = conversationId || await createConversation();
      const pc = new RTCPeerConnection();
      peerRef.current = pc;
      const audio = document.createElement("audio");
      audio.autoplay = true;
      audioRef.current = audio;
      pc.ontrack = (event) => {
        audio.srcObject = event.streams[0];
        void audio.play().catch(() => {
          setLivePlaybackBlocked(true);
          setLiveMessage("Connected, but the browser paused audio output. Tap Resume audio to hear the response.");
        });
      };
      pc.onconnectionstatechange = () => {
        if (peerRef.current !== pc) return;
        if (pc.connectionState === "connected") {
          if (liveDisconnectTimerRef.current !== null) {
            window.clearTimeout(liveDisconnectTimerRef.current);
            liveDisconnectTimerRef.current = null;
          }
          setLiveState("listening");
          if (!livePlaybackBlocked) setLiveMessage("Listening — speak naturally. You can interrupt at any time.");
        }
        if (pc.connectionState === "disconnected") {
          setLiveMessage("Connection interrupted. Trying to recover…");
          if (liveDisconnectTimerRef.current !== null) window.clearTimeout(liveDisconnectTimerRef.current);
          liveDisconnectTimerRef.current = window.setTimeout(() => {
            if (peerRef.current === pc && pc.connectionState === "disconnected") {
              stopLive(false);
              setLiveState("error");
              setLiveMessage("The Live connection ended. You can start again.");
            }
          }, 5_000);
        }
        if (pc.connectionState === "failed") {
          stopLive(false);
          setLiveState("error");
          setLiveMessage("The Live connection ended. You can start again.");
        }
      };
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      streamRef.current = stream;
      stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream));
      const channel = pc.createDataChannel("oai-events");
      channel.onmessage = (event) => {
        try {
          const item = JSON.parse(event.data) as { type?: string; delta?: string; transcript?: string; item_id?: string };
          if (item.type === "conversation.item.input_audio_transcription.delta" && item.delta) {
            inputTranscriptRef.current += item.delta;
            setLiveCaption(`You: ${inputTranscriptRef.current}`);
          }
          if (item.type === "conversation.item.input_audio_transcription.completed" && item.transcript && activeId) {
            inputTranscriptRef.current = item.transcript;
            setLiveCaption(`You: ${item.transcript}`);
            void persistLiveTranscript(activeId, "user", item.transcript, `input:${item.item_id || item.transcript}`);
          }
          if (item.type === "response.output_audio_transcript.delta" && item.delta) {
            outputTranscriptRef.current += item.delta;
            setLiveCaption(`GPT: ${outputTranscriptRef.current}`);
          }
          if (item.type === "response.output_audio_transcript.done" && item.transcript && activeId) {
            outputTranscriptRef.current = item.transcript;
            setLiveCaption(`GPT: ${item.transcript}`);
            void persistLiveTranscript(activeId, "assistant", item.transcript, `output:${item.item_id || item.transcript}`);
            inputTranscriptRef.current = "";
            outputTranscriptRef.current = "";
          }
        } catch { /* Realtime events are best-effort UI updates. */ }
      };
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      const params = new URLSearchParams({ project_id: project });
      if (activeId) params.set("conversation_id", activeId);
      const response = await fetch(`/api/realtime/session?${params}`, { method: "POST", body: offer.sdp, headers: { "Content-Type": "application/sdp" } });
      if (!response.ok) throw new Error(`Live session failed (${response.status})`);
      await pc.setRemoteDescription({ type: "answer", sdp: await response.text() });
    } catch (error) {
      stopLive(false);
      setLiveState("error");
      setLiveMessage(error instanceof DOMException && error.name === "NotAllowedError" ? "Microphone access was not allowed. You can enable it in the browser and try again." : "GPT Live could not connect. Check the server configuration and try again.");
    }
  }

  function changeMode(next: "text" | "live") {
    if (next === mode) return;
    if (mode === "live") stopLive();
    setMode(next);
  }

  function openMemoryDialog(message: UiMessage, index: number, trigger: HTMLElement) {
    memoryReturnFocusRef.current = trigger;
    setMemoryTarget({ ...message, index });
    setMemoryText(message.content.trim());
    setMemoryKind(message.role === "user" ? "preference" : "fact");
    setMemoryState("idle");
  }

  function closeMemoryDialog() {
    setMemoryTarget(undefined);
    setMemoryText("");
    setMemoryState("idle");
    window.requestAnimationFrame(() => memoryReturnFocusRef.current?.focus());
  }

  function closeHistory() {
    setHistoryOpen(false);
    window.requestAnimationFrame(() => historyTriggerRef.current?.focus());
  }

  async function saveMemory() {
    const normalized = memoryText.trim();
    if (!memoryTarget || !conversationId || !normalized || memoryState === "saving") return;
    setMemoryState("saving");
    const messageRef = memoryTarget.id ? `message:${memoryTarget.id}` : `turn:${memoryTarget.index + 1}`;
    try {
      await apiJson("/api/memory", {
        method: "POST",
        body: JSON.stringify({
          type: memoryKind,
          text: normalized,
          source: `conversation:${conversationId}:${messageRef}`,
          confidence: 1,
          project_id: project,
        }),
      });
      setMemoryState("saved");
    } catch {
      setMemoryState("error");
    }
  }

  function handleMemoryDialogKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      closeMemoryDialog();
      return;
    }
    trapFocus(event);
  }

  function handleHistoryKeys(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeHistory();
      return;
    }
    trapFocus(event);
  }

  const history = (
    <div className="space-y-4">
      <div className="flex gap-2">
        <select className="field min-w-0 flex-1" value={projectFilter} onChange={(event) => { setProjectFilter(event.target.value); void loadConversations(event.target.value); }} aria-label="Filter conversations by project">
          <option value="all">All projects</option>{projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <button className="icon-button border border-line" onClick={() => void createConversation().then(() => { if (historyOpen) closeHistory(); })} disabled={!model || running} aria-label="New conversation"><Plus aria-hidden size={18} /></button>
      </div>
      <div className="scrollbar-subtle max-h-[calc(100vh-180px)] space-y-1.5 overflow-y-auto pr-1">
        {conversations.length === 0 && <p className="rounded-control bg-surface-subtle/55 px-3 py-4 text-sm leading-6 text-text-secondary">No conversations yet.</p>}
        {conversations.map((item) => <button key={item.id} className={`w-full rounded-control px-3 py-3 text-left ${item.id === conversationId ? "bg-accent-soft" : "hover:bg-surface-subtle"}`} onClick={() => void openConversation(item.id)} disabled={running || loadingConversation} aria-current={item.id === conversationId ? "true" : undefined}><span className="block truncate text-sm font-medium">{item.title}</span><span className="mt-1 block truncate text-xs text-text-tertiary">{item.project_id || "general"} · {new Date(item.updated_at).toLocaleDateString()}</span></button>)}
      </div>
    </div>
  );

  if (apiError) return <ErrorState title="Chat is not connected" detail="The local API is unavailable. Start the service, then refresh to restore providers, projects, and conversation history." />;

  return (
    <div className="h-[100dvh] md:h-auto md:space-y-3 lg:grid lg:grid-cols-[232px_minmax(0,1fr)] lg:gap-4 lg:space-y-0">
      <aside className="hidden rounded-card border border-line bg-surface/55 p-3 lg:block" aria-label="Conversation history"><div className="mb-4 flex items-center gap-2 px-2 pt-1"><History aria-hidden size={16} className="text-text-tertiary" /><h2 className="text-sm font-medium">Conversations</h2></div>{history}</aside>

      <section className="flex h-[100dvh] min-h-0 w-full min-w-0 flex-col overflow-hidden bg-background md:panel-elevated md:h-[calc(100vh-48px)] md:min-h-[680px]" aria-label="Chat workspace">
        <header className="flex min-h-[58px] items-center gap-2 border-b border-line px-2 pt-[env(safe-area-inset-top)] sm:px-4 md:pt-0">
          <Link href="/" className="icon-button" aria-label="Back to home"><ArrowLeft aria-hidden size={21} /></Link>
          <div className="min-w-0 flex-1 text-center"><h1 className="truncate text-[15px] font-medium">{title}</h1><p className="text-[11px] text-text-tertiary">{mode === "live" ? "GPT Live" : "Text conversation"}</p></div>
          <button ref={historyTriggerRef} className="icon-button" onClick={() => setHistoryOpen(true)} aria-label="Open conversation history"><MoreHorizontal aria-hidden size={21} /></button>
        </header>

        <div className="grid min-h-[104px] grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] items-center gap-2 border-b border-line px-3 py-2 sm:flex sm:min-h-[52px] sm:gap-1 sm:py-1.5">
          <label className="min-w-0 sm:shrink-0"><span className="sr-only">Project context</span><select className="h-10 w-full rounded-full bg-surface-subtle px-3 text-xs font-medium outline-none sm:max-w-28" value={project} disabled={Boolean(conversationId)} onChange={(event) => setProject(event.target.value)}>{projects.length === 0 ? <option value="general">General</option> : projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <div className="min-w-0 [&>div>button]:w-full sm:shrink-0 sm:scale-[0.92] sm:origin-left"><ModelSelector providers={providers} provider={provider} model={model} onChange={(nextProvider, nextModel) => { setProvider(nextProvider); setModel(nextModel); }} /></div>
          <div className="col-span-2 grid grid-cols-2 rounded-full bg-surface-subtle p-1 sm:ml-auto sm:flex sm:shrink-0" role="group" aria-label="Conversation mode">
            <button onClick={() => changeMode("text")} className={`flex h-10 items-center justify-center gap-1.5 rounded-full px-3 text-xs font-medium ${mode === "text" ? "bg-surface-elevated shadow-soft" : "text-text-secondary"}`} aria-pressed={mode === "text"}><MessageCircle aria-hidden size={14} />Text</button>
            <button onClick={() => changeMode("live")} className={`flex h-10 items-center justify-center gap-1.5 rounded-full px-3 text-xs font-medium ${mode === "live" ? "bg-surface-elevated shadow-soft" : "text-text-secondary"}`} aria-pressed={mode === "live"}><Mic2 aria-hidden size={14} />Live</button>
          </div>
        </div>

        {mode === "text" ? (
          <>
            <div ref={conversationRef} className="scrollbar-subtle min-h-0 flex-1 overflow-y-auto" aria-live="polite" aria-busy={running || loadingConversation}>
              <div className="mx-auto w-full max-w-[780px] px-5 py-8 sm:px-6 sm:py-10">
                {loadingConversation && <div className="space-y-3" role="status"><div className="skeleton h-4 w-24" /><div className="skeleton h-20 w-4/5" /></div>}
                {!loadingConversation && messages.length === 0 && (
                  <div className="mx-auto flex min-h-[520px] max-w-lg flex-col justify-start pt-32 sm:min-h-[560px] sm:justify-center sm:pt-0">
                    <div className="relative mx-auto h-28 w-40 overflow-hidden rounded-[28px]">
                      <Image src="/assets/personal-ai-flow.png" alt="" fill sizes="160px" className="scale-[1.18] object-cover" />
                    </div>
                    <h2 className="mt-7 text-center text-[28px] font-medium leading-tight tracking-[-0.035em]">What should we work on?</h2>
                    <p className="mt-3 hidden text-center text-sm leading-6 text-text-secondary sm:block">Start with a question, a plan, or something you want to understand.</p>
                    <div className="mt-7 divide-y divide-line border-y border-line">
                      {starterPrompts.map(({ label, prompt, Icon }) => <button key={label} type="button" className="group flex min-h-14 w-full items-center gap-3 text-left text-sm" onClick={() => setInput(prompt)}><Icon aria-hidden className="shrink-0 text-accent-hover" size={18} strokeWidth={1.7} /><span className="flex-1">{label}</span><ArrowLeft aria-hidden className="rotate-180 text-text-tertiary transition-transform group-hover:translate-x-1" size={16} /></button>)}
                    </div>
                  </div>
                )}
                <div className="space-y-8">
                  {messages.map((message, index) => message.role === "user" ? (
                    <div key={message.id || index} className="ml-auto max-w-[88%] sm:max-w-[78%]">
                      <article className="rounded-card bg-accent-soft px-4 py-3 text-sm leading-7"><RichMessage content={message.content} /></article>
                      {message.content && conversationId && !running && <button type="button" className="mt-1 inline-flex min-h-11 items-center gap-1.5 rounded-control px-2 text-xs font-medium text-text-tertiary hover:bg-surface-subtle hover:text-text-primary" onClick={(event) => openMemoryDialog(message, index, event.currentTarget)}><BookmarkPlus aria-hidden size={14} />Save to Memory</button>}
                    </div>
                  ) : message.role === "system" ? (
                    <article key={message.id || index} className="rounded-control border border-danger/25 bg-surface px-4 py-3 text-sm leading-6 text-danger">{message.content}</article>
                  ) : (
                    <article key={message.id || index} className="grid grid-cols-[24px_minmax(0,1fr)] gap-3 text-[15px]">
                      <Sparkles aria-hidden className="mt-2 text-accent" size={17} />
                      <div className="min-w-0">
                        {message.content ? <RichMessage content={message.content} /> : <span className="mt-2 text-sm text-text-tertiary">Responding…</span>}
                        {message.content && conversationId && !running && <button type="button" className="mt-1 inline-flex min-h-11 items-center gap-1.5 rounded-control px-2 text-xs font-medium text-text-tertiary hover:bg-surface-subtle hover:text-text-primary" onClick={(event) => openMemoryDialog(message, index, event.currentTarget)}><BookmarkPlus aria-hidden size={14} />Save to Memory</button>}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            </div>
            <ActivityPanel trace={trace} />
            <form onSubmit={submit} className="bg-surface px-3 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 sm:px-5 sm:pb-5">
              {useMcp && <div className="mx-auto mb-2 grid max-w-[780px] gap-2 rounded-control bg-surface-subtle p-2 sm:grid-cols-2"><label className="text-xs font-medium text-text-secondary">Connector<select className="field mt-1 w-full" value={connectorId} onChange={(event) => selectConnector(event.target.value)}><option value="local-reference">Built-in reference</option>{connectors.filter((item) => item.enabled).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.connection_status}</option>)}</select></label><label className="text-xs font-medium text-text-secondary">Tool<select className="field mt-1 w-full" value={toolName} onChange={(event) => setToolName(event.target.value)}>{(connectorId === "local-reference" ? ["system.echo"] : selectedConnector?.allowed_tools || []).map((item) => <option key={item} value={item}>{item}</option>)}</select></label></div>}
              {providers.length > 0 && !providerReady && <div className="mx-auto mb-2 flex max-w-[780px] items-center justify-between gap-3 rounded-control bg-warning/10 px-3 py-2 text-xs text-warning"><span>{selectedProvider?.id === "anthropic" ? "Anthropic" : "OpenAI"} needs a server-side credential before messages can be sent.</span><Link href="/settings#models-settings" className="shrink-0 font-medium underline underline-offset-2">Open Settings</Link></div>}
              <div className="mx-auto max-w-[780px] rounded-[22px] border border-line-strong bg-surface-elevated p-2 shadow-composer focus-within:border-accent">
                <textarea className="scrollbar-subtle max-h-40 min-h-[48px] w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-6 outline-none placeholder:text-text-tertiary" placeholder="Ask anything…" aria-label="Message" value={input} rows={1} onChange={(event) => setInput(event.target.value)} />
                <div className="flex items-center gap-1"><button type="button" className="icon-button" disabled title="Attachments are planned" aria-label="Attach a file (planned)"><Paperclip aria-hidden size={18} /></button><button type="button" className={`icon-button ${useMcp ? "bg-accent-soft text-accent" : ""}`} onClick={() => setUseMcp((current) => !current)} aria-pressed={useMcp} aria-label="Use an MCP tool"><Wrench aria-hidden size={18} /></button><button className="button-primary ml-auto size-10 min-h-10 px-0" aria-label={running ? "Sending message" : "Send message"} disabled={!input.trim() || !model || !providerReady || running || (useMcp && !toolName)}><Send aria-hidden size={17} /></button></div>
              </div>
            </form>
          </>
        ) : (
          <div className="relative flex min-h-0 flex-1 flex-col items-center justify-center overflow-hidden px-6 pb-[max(28px,env(safe-area-inset-bottom))] text-center">
            <div className={`relative grid size-52 place-items-center overflow-hidden rounded-full transition duration-500 ${liveState === "listening" ? "scale-105 shadow-composer" : ""}`}><img src="/assets/personal-ai-flow.png" alt="" className="absolute inset-0 h-full w-full scale-[1.8] object-cover" /><span className={`relative grid size-20 place-items-center rounded-full bg-surface-elevated/90 text-accent-hover shadow-soft ${liveState === "listening" ? "animate-pulse" : ""}`}><Mic2 aria-hidden size={30} strokeWidth={1.6} /></span></div>
            <h2 className="mt-8 text-[28px] font-medium tracking-[-0.035em]">{liveState === "listening" ? "I’m listening" : liveState === "connecting" ? "Connecting…" : "Talk it through"}</h2>
            <p className={`mt-3 max-w-md text-sm leading-6 ${liveState === "error" ? "text-danger" : "text-text-secondary"}`}>{realtime && !realtime.configured && liveState === "idle" ? "GPT Live needs a server-side Realtime credential before this phone can start a voice conversation." : liveMessage}</p>
            {liveCaption && <p className="mt-5 max-w-lg rounded-card bg-surface/75 px-4 py-3 text-sm leading-6 text-text-primary">{liveCaption}</p>}
            {liveSaveWarning && <p className="mt-3 max-w-md text-xs leading-5 text-warning">{liveSaveWarning}</p>}
            {livePlaybackBlocked && <button type="button" className="button-secondary mt-4" onClick={() => void resumeLiveAudio()}>Resume audio</button>}
            <p className="mt-4 text-xs text-text-tertiary">{realtime?.model || "Realtime model"} · WebRTC · {project}</p>
            <p className="mt-2 max-w-md text-[11px] leading-5 text-text-tertiary">Completed Live transcripts stay in this conversation and can create its short title. They are not added to Memory automatically.</p>
            {liveState === "listening" || liveState === "connecting" ? <button onClick={() => stopLive()} className="mt-8 inline-flex size-16 items-center justify-center rounded-full bg-text-primary text-surface-elevated shadow-composer" aria-label="End live conversation"><Square aria-hidden size={21} fill="currentColor" /></button> : realtime && !realtime.configured ? <Link href="/settings#mobile-settings" className="mt-8 inline-flex min-h-14 items-center justify-center gap-2 rounded-full bg-text-primary px-7 text-sm font-medium text-surface-elevated shadow-composer"><Wrench aria-hidden size={18} />Configure GPT Live</Link> : <button onClick={() => void startLive()} className="mt-8 inline-flex min-h-14 items-center justify-center gap-2 rounded-full bg-text-primary px-7 text-sm font-medium text-surface-elevated shadow-composer" disabled={!realtime}><Mic2 aria-hidden size={18} />{realtime ? "Start GPT Live" : "Checking GPT Live…"}</button>}
          </div>
        )}
      </section>

      {historyOpen && <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-text-primary/20" onClick={closeHistory} aria-label="Close conversation history" /><aside ref={historyDialogRef} role="dialog" aria-modal="true" aria-label="Conversation history" className="absolute inset-y-0 right-0 w-[min(340px,90vw)] border-l border-line bg-surface-elevated p-4 shadow-composer" onKeyDown={handleHistoryKeys}><div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-medium">Conversations</h2><button className="icon-button" onClick={closeHistory} aria-label="Close conversation history"><X aria-hidden size={20} /></button></div>{history}</aside></div>}

      {memoryTarget && (
        <div className="fixed inset-0 z-[60] flex items-end justify-center md:items-center md:p-6">
          <button className="absolute inset-0 bg-text-primary/25" onClick={closeMemoryDialog} aria-label="Close save to memory" />
          <section ref={memoryDialogRef} role="dialog" aria-modal="true" aria-labelledby="save-memory-title" className="relative w-full rounded-t-[28px] border border-line bg-surface-elevated px-5 pb-[max(24px,env(safe-area-inset-bottom))] pt-4 shadow-composer md:max-w-lg md:rounded-card md:p-6" onKeyDown={handleMemoryDialogKeyDown}>
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line-strong md:hidden" aria-hidden />
            <div className="flex items-start justify-between gap-4">
              <div><p className="eyebrow">Long-term memory</p><h2 id="save-memory-title" className="mt-1 text-xl font-medium tracking-[-0.02em]">Save what matters</h2></div>
              <button type="button" className="icon-button -mr-2 -mt-2" onClick={closeMemoryDialog} aria-label="Close save to memory"><X aria-hidden size={20} /></button>
            </div>
            <p className="mt-3 text-sm leading-6 text-text-secondary">Only this reviewed note will be saved. The rest of the conversation stays out of long-term Memory.</p>
            <div className="scrollbar-subtle mt-5 flex gap-2 overflow-x-auto pb-1" role="group" aria-label="Memory type">
              {(["fact", "preference", "rule", "project"] as MemoryKind[]).map((item) => <button key={item} type="button" className={`chip min-h-11 shrink-0 capitalize ${memoryKind === item ? "bg-accent-soft text-accent-hover" : ""}`} aria-pressed={memoryKind === item} onClick={() => setMemoryKind(item)}>{item}</button>)}
            </div>
            <label className="mt-4 block text-xs font-medium text-text-secondary">Memory note<textarea className="textarea-field mt-2 min-h-36 w-full resize-y text-[15px] leading-6" value={memoryText} onChange={(event) => { setMemoryText(event.target.value); if (memoryState !== "idle") setMemoryState("idle"); }} /></label>
            <p className="mt-2 text-xs text-text-tertiary">Project: {projects.find((item) => item.id === project)?.name || project} · Source: this conversation</p>
            {memoryState === "error" && <p className="mt-3 text-sm text-danger" role="alert">This note could not be saved. Check the local API and try again.</p>}
            <p className="sr-only" role="status" aria-live="polite">{memoryState === "saved" ? "Memory saved." : memoryState === "saving" ? "Saving memory." : ""}</p>
            <div className="mt-5 flex gap-3">
              <button type="button" className="button-secondary flex-1" onClick={closeMemoryDialog}>Cancel</button>
              <button type="button" className="button-primary flex-1" onClick={() => void saveMemory()} disabled={!memoryText.trim() || memoryState === "saving" || memoryState === "saved"}>{memoryState === "saved" ? <><Check aria-hidden size={17} />Saved</> : memoryState === "saving" ? "Saving…" : "Save memory"}</button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
