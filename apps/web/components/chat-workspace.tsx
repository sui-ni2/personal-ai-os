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
    if (mobilePreview) {
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
      return () => { cancelled = true; stopLive(false); };
    }
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
        if (item.type === "error") setMessages((current) => current.map((message, index) => index === current.length - 1 ? { role: "system", content: "The request could not be completed. Check your AI service or tool settings, then try again." } : message));
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
      setLiveMessage("Listening â€” speak naturally. You can interrupt at any time.");
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
        constßÍ·¶‰žËkºwµçiµ…àµÜ´ÈàˆÙ…±Õ”õíÁÉ½©•Ñô‘¥Í…‰±•õí	½½±•…¸¡½¹Ù•ÉÍ…Ñ¥½¹%¥ô½¹¡…¹”õì¡•Ù•¹Ð¤€ôøÍ•ÑAÉ½©•Ð¡•Ù•¹Ð¹Ñ…É•Ð¹Ù…±Õ”¥ôùíÁÉ½©•ÑÌ¹±•¹Ñ €ôôô€À€ü€ñ½ÁÑ¥½¸Ù…±Õ”ô‰•¹•É…°ˆù•¹•É…°ð½½ÁÑ¥½¸ø€èÁÉ½©•ÑÌ¹µ…À ¡¥Ñ•´¤€ôø€ñ½ÁÑ¥½¸­•äõí¥Ñ•´¹¥‘ôÙ…±Õ”õí¥Ñ•´¹¥‘ôùí¥Ñ•´¹¹…µ•ôð½½ÁÑ¥½¸ø¥ôð½Í•±•Ðøð½±…‰•°ø4(€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰µ¥¸µÜ´Àl˜ù‘¥Øù‰ÕÑÑ½¹téÜµ™Õ±°Í´éÍ¡É¥¹¬´ÀÍ´éÍ…±”µlÀ¸äÉtÍ´é½É¥¥¸µ±•™Ðˆøñ5½‘•±M•±•Ñ½ÈÁÉ½Ù¥‘•ÉÌõíÁÉ½Ù¥‘•ÉÍôÁÉ½Ù¥‘•ÈõíÁÉ½Ù¥‘•Éôµ½‘•°õíµ½‘•±ô½¹¡…¹”õì¡¹•áÑAÉ½Ù¥‘•È°¹•áÑ5½‘•°¤€ôøìÍ•ÑAÉ½Ù¥‘•È¡¹•áÑAÉ½Ù¥‘•È¤ìÍ•Ñ5½‘•°¡¹•áÑ5½‘•°¤ìõô€¼øð½‘¥Øø4(€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰½°µÍÁ…¸´ÈÉ¥É¥µ½±Ì´ÈÉ½Õ¹‘•µ™Õ±°‰œµÍÕÉ™…”µÍÕ‰Ñ±”À´ÄÍ´éµ°µ…ÕÑ¼Í´é™±•àÍ´éÍ¡É¥¹¬´ÀˆÉ½±”ô‰É½ÕÀˆ…É¥„µ±…‰•°ô‰½¹Ù•ÉÍ…Ñ¥½¸µ½‘”ˆø4(€€€€€€€€€€€€ñ‰ÕÑÑ½¸½¹±¥¬õì ¤€ôø¡…¹•5½‘” ‰Ñ•áÐˆ¥ô±…ÍÍ9…µ”õí™±•à ´ÄÀ¥Ñ•µÌµ•¹Ñ•È©ÕÍÑ¥™äµ•¹Ñ•È…À´Ä¸ÔÉ½Õ¹‘•µ™Õ±°Áà´ÌÑ•áÐµáÌ™½¹Ðµµ•‘¥Õ´€‘íµ½‘”€ôôô€‰Ñ•áÐˆ€ü€‰‰œµÍÕÉ™…”µ•±•Ù…Ñ•Í¡…‘½ÜµÍ½™Ðˆ€è€‰Ñ•áÐµÑ•áÐµÍ•½¹‘…Éä‰õô…É¥„µÁÉ•ÍÍ•õíµ½‘”€ôôô€‰Ñ•áÐ‰ôøñ5•ÍÍ…•¥É±”…É¥„µ¡¥‘‘•¸Í¥é”õìÄÑô€¼ùQ•áÐð½‰ÕÑÑ½¸ø4(€€€€€€€€€€€€ñ‰ÕÑÑ½¸½¹±¥¬õì ¤€ôø¡…¹•5½‘” ‰±¥Ù”ˆ¥ô±…ÍÍ9…µ”õí™±•à ´ÄÀ¥Ñ•µÌµ•¹Ñ•È©ÕÍÑ¥™äµ•¹Ñ•È…À´Ä¸ÔÉ½Õ¹‘•µ™Õ±°Áà´ÌÑ•áÐµáÌ™½¹Ðµµ•‘¥Õ´€‘íµ½‘”€ôôô€‰±¥Ù”ˆ€ü€‰‰œµÍÕÉ™…”µ•±•Ù…Ñ•Í¡…‘½ÜµÍ½™Ðˆ€è€‰Ñ•áÐµÑ•áÐµÍ•½¹‘…Éä‰õô…É¥„µÁÉ•ÍÍ•õíµ½‘”€ôôô€‰±¥Ù”‰ôøñ5¥ŒÈ…É¥„µ¡¥‘‘•¸Í¥é”õìÄÑô€¼ù1¥Ù”ð½‰ÕÑÑ½¸ø4(€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€ð½‘¥Øø4(4(€€€€€€€íµ½‘”€ôôô€‰Ñ•áÐˆ€ü€ 4(€€€€€€€€€€ðø4(€€€€€€€€€€€€ñ‘¥ØÉ•˜õí½¹Ù•ÉÍ…Ñ¥½¹I•™ô±…ÍÍ9…µ”ô‰ÍÉ½±±‰…ÈµÍÕ‰Ñ±”µ¥¸µ ´À™±•à´Ä½Ù•É™±½Üµäµ…ÕÑ¼ˆ…É¥„µ±¥Ù”ô‰Á½±¥Ñ”ˆ…É¥„µ‰ÕÍäõíÉÕ¹¹¥¹œñð±½…‘¥¹½¹Ù•ÉÍ…Ñ¥½¹ôø4(€€€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰µàµ…ÕÑ¼Üµ™Õ±°µ…àµÜµlÜàÁÁátÁà´ÔÁä´àÍ´éÁà´ØÍ´éÁä´ÄÀˆø4(€€€€€€€€€€€€€€€í±½…‘¥¹½¹Ù•ÉÍ…Ñ¥½¸€˜˜€ñ‘¥Ø±…ÍÍ9…µ”ô‰ÍÁ…”µä´ÌˆÉ½±”ô‰ÍÑ…ÑÕÌˆøñ‘¥Ø±…ÍÍ9…µ”ô‰Í­•±•Ñ½¸ ´ÐÜ´ÈÐˆ€¼øñ‘¥Ø±…ÍÍ9…µ”ô‰Í­•±•Ñ½¸ ´ÈÀÜ´Ð¼Ôˆ€¼øð½‘¥Øùô4(€€€€€€€€€€€€€€€ì…±½…‘¥¹½¹Ù•ÉÍ…Ñ¥½¸€˜˜µ•ÍÍ…•Ì¹±•¹Ñ €ôôô€À€˜˜€ 4(€€€€€€€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰µàµ…ÕÑ¼™±•àµ¥¸µ µlÔÈÁÁátµ…àµÜµ±œ™±•àµ½°©ÕÍÑ¥™äµÍÑ…ÉÐÁÐ´ÌÈÍ´éµ¥¸µ µlÔØÁÁátÍ´é©ÕÍÑ¥™äµ•¹Ñ•ÈÍ´éÁÐ´Àˆø4(€€€€€€€€€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰É•±…Ñ¥Ù”µàµ…ÕÑ¼ ´ÈàÜ´ÐÀ½Ù•É™±½Üµ¡¥‘‘•¸É½Õ¹‘•µlÈáÁátˆø4(€€€€€€€€€€€€€€€€€€€€€€ñ%µ…”ÍÉŒôˆ½…ÍÍ•ÑÌ½Á•ÉÍ½¹…°µ…¤µ™±½Ü¹Á¹œˆ…±Ðôˆˆ™¥±°Í¥é•ÌôˆÄØÁÁàˆ±…ÍÍ9…µ”ô‰Í…±”µlÄ¸Äát½‰©•Ðµ½Ù•Èˆ€¼ø4(€€€€€€€€€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€€€€€€€€€ñ È±…ÍÍ9…µ”ô‰µÐ´ÜÑ•áÐµ•¹Ñ•ÈÑ•áÐµlÈáÁát™½¹Ðµµ•‘¥Õ´±•…‘¥¹œµÑ¥¡ÐÑÉ…­¥¹œµl´À¸ÀÌÕ•µtˆù]¡…ÐÍ¡½Õ±Ý”Ý½É¬½¸üð½ Èø4(€€€€€€€€€€€€€€€€€€€€ñÀ±…ÍÍ9…µ”ô‰µÐ´Ì¡¥‘‘•¸Ñ•áÐµ•¹Ñ•ÈÑ•áÐµÍ´±•…‘¥¹œ´ØÑ•áÐµÑ•áÐµÍ•½¹‘…ÉäÍ´é‰±½¬ˆùMÑ…ÉÐÝ¥Ñ „ÅÕ•ÍÑ¥½¸°„Á±…¸°½ÈÍ½µ•Ñ¡¥¹œå½ÔÝ…¹ÐÑ¼Õ¹‘•ÉÍÑ…¹¸ð½Àø4(€€€€€€€€€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰µÐ´Ü‘¥Ù¥‘”µä‘¥Ù¥‘”µ±¥¹”‰½É‘•Èµä‰½É‘•Èµ±¥¹”ˆø4(€€€€€€€€€€€€€€€€€€€€€íÍÑ…ÉÑ•ÉAÉ½µÁÑÌ¹µ…À ¡ì±…‰•°°ÁÉ½µÁÐ°%½¸ô¤€ôø€ñ‰ÕÑÑ½¸­•äõí±…‰•±ôÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”ô‰É½ÕÀ™±•àµ¥¸µ ´ÄÐÜµ™Õ±°¥Ñ•µÌµ•¹Ñ•È…À´ÌÑ•áÐµ±•™ÐÑ•áÐµÍ´ˆ½¹±¥¬õì ¤€ôøÍ•Ñ%¹ÁÕÐ¡ÁÉ½µÁÐ¥ôøñ%½¸…É¥„µ¡¥‘‘•¸±…ÍÍ9…µ”ô‰Í¡É¥¹¬´ÀÑ•áÐµ…•¹Ðµ¡½Ù•ÈˆÍ¥é”õìÄáôÍÑÉ½­•]¥‘Ñ õìÄ¸Ýô€¼øñÍÁ…¸±…ÍÍ9…µ”ô‰™±•à´Äˆùí±…‰•±ôð½ÍÁ…¸øñÉÉ½Ý1•™Ð…É¥„µ¡¥‘‘•¸±…ÍÍ9…µ”ô‰É½Ñ…Ñ”´ÄàÀÑ•áÐµÑ•áÐµÑ•ÉÑ¥…ÉäÑÉ…¹Í¥Ñ¥½¸µÑÉ…¹Í™½É´É½ÕÀµ¡½Ù•ÈéÑÉ…¹Í±…Ñ”µà´ÄˆÍ¥é”õìÄÙô€¼øð½‰ÕÑÑ½¸ø¥ô4(€€€€€€€€€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€€€€€¥ô4(€€€€€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰ÍÁ…”µä´àˆø4(€€€€€€€€€€€€€€€€€íµ•ÍÍ…•Ì¹µ…À ¡µ•ÍÍ…”°¥¹‘•à¤€ôøµ•ÍÍ…”¹É½±”€ôôô€‰ÕÍ•Èˆ€ü€ 4(€€€€€€€€€€€€€€€€€€€€ñ‘¥Ø­•äõíµ•ÍÍ…”¹¥ñð¥¹‘•áô±…ÍÍ9…µ”ô‰µ°µ…ÕÑ¼µ…àµÜµlàà•tÍ´éµ…àµÜµlÜà•tˆø4(€€€€€€€€€€€€€€€€€€€€€€ñ…ÉÑ¥±”±…ÍÍ9…µ”ô‰É½Õ¹‘•µ…É‰œµ…•¹ÐµÍ½™ÐÁà´ÐÁä´ÌÑ•áÐµÍ´±•…‘¥¹œ´ÜˆøñI¥¡5•ÍÍ…”½¹Ñ•¹Ðõíµ•ÍÍ…”¹½¹Ñ•¹Ñô€¼øð½…ÉÑ¥±”ø4(€€€€€€€€€€€€€€€€€€€€€íµ•ÍÍ…”¹½¹Ñ•¹Ð€˜˜½¹Ù•ÉÍ…Ñ¥½¹%€˜˜€…ÉÕ¹¹¥¹œ€˜˜€ñ‰ÕÑÑ½¸ÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”ô‰µÐ´Ä¥¹±¥¹”µ™±•àµ¥¸µ ´ÄÄ¥Ñ•µÌµ•¹Ñ•È…À´Ä¸ÔÉ½Õ¹‘•µ½¹ÑÉ½°Áà´ÈÑ•áÐµáÌ™½¹Ðµµ•‘¥Õ´Ñ•áÐµÑ•áÐµÑ•ÉÑ¥…Éä¡½Ù•Èé‰œµÍÕÉ™…”µÍÕ‰Ñ±”¡½Ù•ÈéÑ•áÐµÑ•áÐµÁÉ¥µ…Éäˆ½¹±¥¬õì¡•Ù•¹Ð¤€ôø½Á•¹5•µ½Éå¥…±½œ¡µ•ÍÍ…”°¥¹‘•à°•Ù•¹Ð¹ÕÉÉ•¹ÑQ…É•Ð¥ôøñ	½½­µ…É­A±ÕÌ…É¥„µ¡¥‘‘•¸Í¥é”õìÄÑô€¼ùM…Ù”Ñ¼5•µ½Éäð½‰ÕÑÑ½¸ùô4(€€€€€€€€€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€€€€€€€¤€èµ•ÍÍ…”¹É½±”€ôôô€‰ÍåÍÑ•´ˆ€ü€ 4(€€€€€€€€€€€€€€€€€€€€ñ…ÉÑ¥±”­•äõíµ•ÍÍ…”¹¥ñð¥¹‘•áô±…ÍÍ9…µ”ô‰É½Õ¹‘•µ½¹ÑÉ½°‰½É‘•È‰½É‘•Èµ‘…¹•È¼ÈÔ‰œµÍÕÉ™…”Áà´ÐÁä´ÌÑ•áÐµÍ´±•…‘¥¹œ´ØÑ•áÐµ‘…¹•Èˆùíµ•ÍÍ…”¹½¹Ñ•¹Ñôð½…ÉÑ¥±”ø4(€€€€€€€€€€€€€€€€€€¤€è€ 4(€€€€€€€€€€€€€€€€€€€€ñ…ÉÑ¥±”­•äõíµ•ÍÍ…”¹¥ñð¥¹‘•áô±…ÍÍ9…µ”ô‰É¥É¥µ½±ÌµlÈÑÁá}µ¥¹µ…à À°Å™È¥t…À´ÌÑ•áÐµlÄÕÁátˆø4(€€€€€€€€€€€€€€€€€€€€€€ñMÁ…É­±•Ì…É¥„µ¡¥‘‘•¸±…ÍÍ9…µ”ô‰µÐ´ÈÑ•áÐµ…•¹ÐˆÍ¥é”õìÄÝô€¼ø4(€€€€€€€€€€€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰µ¥¸µÜ´Àˆø4(€€€€€€€€€€€€€€€€€€€€€€€íµ•ÍÍ…”¹½¹Ñ•¹Ð€ü€ñI¥¡5•ÍÍ…”½¹Ñ•¹Ðõíµ•ÍÍ…”¹½¹Ñ•¹Ñô€¼ø€è€ñÍÁ…¸±…ÍÍ9…µ”ô‰µÐ´ÈÑ•áÐµÍ´Ñ•áÐµÑ•áÐµÑ•ÉÑ¥…ÉäˆùI•ÍÁ½¹‘¥¹ŸŠ˜ð½ÍÁ…¸ùô4(€€€€€€€€€€€€€€€€€€€€€€€íµ•ÍÍ…”¹½¹Ñ•¹Ð€˜˜½¹Ù•ÉÍ…Ñ¥½¹%€˜˜€…ÉÕ¹¹¥¹œ€˜˜€ñ‰ÕÑÑ½¸ÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”ô‰µÐ´Ä¥¹±¥¹”µ™±•àµ¥¸µ ´ÄÄ¥Ñ•µÌµ•¹Ñ•È…À´Ä¸ÔÉ½Õ¹‘•µ½¹ÑÉ½°Áà´ÈÑ•áÐµáÌ™½¹Ðµµ•‘¥Õ´Ñ•áÐµÑ•áÐµÑ•ÉÑ¥…Éä¡½Ù•Èé‰œµÍÕÉ™…”µÍÕ‰Ñ±”¡½Ù•ÈéÑ•áÐµÑ•áÐµÁÉ¥µ…Éäˆ½¹±¥¬õì¡•Ù•¹Ð¤€ôø½Á•¹5•µ½Éå¥…±½œ¡µ•ÍÍ…”°¥¹‘•à°•Ù•¹Ð¹ÕÉÉ•¹ÑQ…É•Ð¥ôøñ	½½­µ…É­A±ÕÌ…É¥„µ¡¥‘‘•¸Í¥é”õìÄÑô€¼ùM…Ù”Ñ¼5•µ½Éäð½‰ÕÑÑ½¸ùô4(€€€€€€€€€€€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€€€€€€€€€ð½…ÉÑ¥±”ø4(€€€€€€€€€€€€€€€€€€¤¥ô4(€€€€€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€ñÑ¥Ù¥ÑåA…¹•°ÑÉ…”õíÑÉ…•ô€¼ø4(€€€€€€€€€€€€ñ™½É´½¹MÕ‰µ¥ÐõíÍÕ‰µ¥Ñô±…ÍÍ9…µ”ô‰‰œµÍÕÉ™…”Áà´ÌÁˆµmµ…à ÄÉÁà±•¹Ø¡Í…™”µ…É•„µ¥¹Í•Ðµ‰½ÑÑ½´¤¥tÁÐ´ÌÍ´éÁà´ÔÍ´éÁˆ´Ôˆø4(€€€€€€€€€€€€€íÕÍ•5À€˜˜€ñ‘¥Ø±…ÍÍ9…µ”ô‰µàµ…ÕÑ¼µˆ´ÈÉ¥µ…àµÜµlÜàÁÁát…À´ÈÉ½Õ¹‘•µ½¹ÑÉ½°‰œµÍÕÉ™…”µÍÕ‰Ñ±”À´ÈÍ´éÉ¥µ½±Ì´Èˆøñ±…‰•°±…ÍÍ9…µ”ô‰Ñ•áÐµáÌ™½¹Ðµµ•‘¥Õ´Ñ•áÐµÑ•áÐµÍ•½¹‘…Éäˆù½¹¹•Ñ½ÈñÍ•±•Ð±…ÍÍ9…µ”ô‰™¥•±µÐ´ÄÜµ™Õ±°ˆÙ…±Õ”õí½¹¹•Ñ½É%‘ô½¹¡…¹”õì¡•Ù•¹Ð¤€ôøÍ•±•Ñ½¹¹•Ñ½È¡•Ù•¹Ð¹Ñ…É•Ð¹Ù…±Õ”¥ôøñ½ÁÑ¥½¸Ù…±Õ”ô‰±½…°µÉ•™•É•¹”ˆù	Õ¥±Ðµ¥¸É•™•É•¹”ð½½ÁÑ¥½¸ùí½¹¹•Ñ½ÉÌ¹™¥±Ñ•È ¡¥Ñ•´¤€ôø¥Ñ•´¹•¹…‰±•¤¹µ…À ¡¥Ñ•´¤€ôø€ñ½ÁÑ¥½¸­•äõí¥Ñ•´¹¥‘ôÙ…±Õ”õí¥Ñ•´¹¥‘ôùí¥Ñ•´¹¹…µ•ôƒ
Üí¥Ñ•´¹½¹¹•Ñ¥½¹}ÍÑ…ÑÕÍôð½½ÁÑ¥½¸ø¥ôð½Í•±•Ðøð½±…‰•°øñ±…‰•°±…ÍÍ9…µ”ô‰Ñ•áÐµáÌ™½¹Ðµµ•‘¥Õ´Ñ•áÐµÑ•áÐµÍ•½¹‘…ÉäˆùQ½½°ñÍ•±•Ð±…ÍÍ9…µ”ô‰™¥•±µÐ´ÄÜµ™Õ±°ˆÙ…±Õ”õíÑ½½±9…µ•ô½¹¡…¹”õì¡•Ù•¹Ð¤€ôøÍ•ÑQ½½±9…µ”¡•Ù•¹Ð¹Ñ…É•Ð¹Ù…±Õ”¥ôùì¡½¹¹•Ñ½É%€ôôô€‰±½…°µÉ•™•É•¹”ˆ€ül‰ÍåÍÑ•´¹•¡¼‰t€èÍ•±•Ñ•‘½¹¹•Ñ½Èü¹…±±½Ý•‘}Ñ½½±Ìñðmt¤¹µ…À ¡¥Ñ•´¤€ôø€ñ½ÁÑ¥½¸­•äõí¥Ñ•µôÙ…±Õ”õí¥Ñ•µôùí¥Ñ•µôð½½ÁÑ¥½¸ø¥ôð½Í•±•Ðøð½±…‰•°øð½‘¥Øùô4(€€€€€€€€€€€€€íÁÉ½Ù¥‘•ÉÌ¹±•¹Ñ €ø€À€˜˜€…ÁÉ½Ù¥‘•ÉI•…‘ä€˜˜€ñ‘¥Ø±…ÍÍ9…µ”ô‰µàµ…ÕÑ¼µˆ´È™±•àµ…àµÜµlÜàÁÁát¥Ñ•µÌµ•¹Ñ•È©ÕÍÑ¥™äµ‰•ÑÝ••¸…À´ÌÉ½Õ¹‘•µ½¹ÑÉ½°‰œµÝ…É¹¥¹œ¼ÄÀÁà´ÌÁä´ÈÑ•áÐµáÌÑ•áÐµÝ…É¹¥¹œˆøñÍÁ…¸ùíÍ•±•Ñ•‘AÉ½Ù¥‘•Èü¹¥€ôôô€‰…¹Ñ¡É½Á¥Œˆ€ü€‰¹Ñ¡É½Á¥Œˆ€è€‰=Á•¹$‰ô¹••‘Ì„Í•ÉÙ•ÈµÍ¥‘”É•‘•¹Ñ¥…°‰•™½É”µ•ÍÍ…•Ì…¸‰”Í•¹Ð¸ð½ÍÁ…¸øñ1¥¹¬¡É•˜ôˆ½Í•ÑÑ¥¹Ìµ½‘•±ÌµÍ•ÑÑ¥¹Ìˆ±…ÍÍ9…µ”ô‰Í¡É¥¹¬´À™½¹Ðµµ•‘¥Õ´Õ¹‘•É±¥¹”Õ¹‘•É±¥¹”µ½™™Í•Ð´Èˆù=Á•¸M•ÑÑ¥¹Ìð½1¥¹¬øð½‘¥Øùô4(€€€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰µàµ…ÕÑ¼µ…àµÜµlÜàÁÁátÉ½Õ¹‘•µlÈÉÁát‰½É‘•È‰½É‘•Èµ±¥¹”µÍÑÉ½¹œ‰œµÍÕÉ™…”µ•±•Ù…Ñ•À´ÈÍ¡…‘½Üµ½µÁ½Í•È™½ÕÌµÝ¥Ñ¡¥¸é‰½É‘•Èµ…•¹Ðˆø4(€€€€€€€€€€€€€€€€ñÑ•áÑ…É•„±…ÍÍ9…µ”ô‰ÍÉ½±±‰…ÈµÍÕ‰Ñ±”µ…àµ ´ÐÀµ¥¸µ µlÐáÁátÜµ™Õ±°É•Í¥é”µ¹½¹”‰œµÑÉ…¹ÍÁ…É•¹ÐÁà´ÈÁä´ÈÑ•áÐµlÄÕÁát±•…‘¥¹œ´Ø½ÕÑ±¥¹”µ¹½¹”Á±…•¡½±‘•ÈéÑ•áÐµÑ•áÐµÑ•ÉÑ¥…ÉäˆÁ±…•¡½±‘•Èô‰Í¬…¹åÑ¡¥¹ŸŠ˜ˆ…É¥„µ±…‰•°ô‰5•ÍÍ…”ˆÙ…±Õ”õí¥¹ÁÕÑôÉ½ÝÌõìÅô½¹¡…¹”õì¡•Ù•¹Ð¤€ôøÍ•Ñ%¹ÁÕÐ¡•Ù•¹Ð¹Ñ…É•Ð¹Ù…±Õ”¥ô€¼ø4(€€€€€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰™±•à¥Ñ•µÌµ•¹Ñ•È…À´Äˆøñ‰ÕÑÑ½¸ÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”ô‰¥½¸µ‰ÕÑÑ½¸ˆ‘¥Í…‰±•Ñ¥Ñ±”ô‰ÑÑ…¡µ•¹ÑÌ…É”Á±…¹¹•ˆ…É¥„µ±…‰•°ô‰ÑÑ… „™¥±”€¡Á±…¹¹•¤ˆøñA…Á•É±¥À…É¥„µ¡¥‘‘•¸Í¥é”õìÄáô€¼øð½‰ÕÑÑ½¸øñ‰ÕÑÑ½¸ÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”õí¥½¸µ‰ÕÑÑ½¸€‘íÕÍ•5À€ü€‰‰œµ…•¹ÐµÍ½™ÐÑ•áÐµ…•¹Ðˆ€è€ˆ‰õô½¹±¥¬õì ¤€ôøÍ•ÑUÍ•5À ¡ÕÉÉ•¹Ð¤€ôø€…ÕÉÉ•¹Ð¥ô…É¥„µÁÉ•ÍÍ•õíÕÍ•5Áô…É¥„µ±…‰•°ô‰UÍ”„Ñ½½°ˆøñ]É•¹ …É¥„µ¡¥‘‘•¸Í¥é”õìÄáô€¼øð½‰ÕÑÑ½¸øñ‰ÕÑÑ½¸±…ÍÍ9…µ”ô‰‰ÕÑÑ½¸µÁÉ¥µ…Éäµ°µ…ÕÑ¼Í¥é”´ÄÀµ¥¸µ ´ÄÀÁà´Àˆ…É¥„µ±…‰•°õíÉÕ¹¹¥¹œ€ü€‰M•¹‘¥¹œµ•ÍÍ…”ˆ€è€‰M•¹µ•ÍÍ…”‰ô‘¥Í…‰±•õì…¥¹ÁÕÐ¹ÑÉ¥´ ¤ñð€…µ½‘•°ñð€…ÁÉ½Ù¥‘•ÉI•…‘äñðÉÕ¹¹¥¹œñð€¡ÕÍ•5À€˜˜€…Ñ½½±9…µ”¥ôøñM•¹…É¥„µ¡¥‘‘•¸Í¥é”õìÄÝô€¼øð½‰ÕÑÑ½¸øð½‘¥Øø(€€€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€ð½™½É´ø4(€€€€€€€€€€ð¼ø4(€€€€€€€€¤€è€ 4(€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰É•±…Ñ¥Ù”™±•àµ¥¸µ ´À™±•à´Ä™±•àµ½°¥Ñ•µÌµ•¹Ñ•È©ÕÍÑ¥™äµ•¹Ñ•È½Ù•É™±½Üµ¡¥‘‘•¸Áà´ØÁˆµmµ…à ÈáÁà±•¹Ø¡Í…™”µ…É•„µ¥¹Í•Ðµ‰½ÑÑ½´¤¥tÑ•áÐµ•¹Ñ•Èˆø4(€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”õíÉ•±…Ñ¥Ù”É¥Í¥é”´ÔÈÁ±…”µ¥Ñ•µÌµ•¹Ñ•È½Ù•É™±½Üµ¡¥‘‘•¸É½Õ¹‘•µ™Õ±°ÑÉ…¹Í¥Ñ¥½¸‘ÕÉ…Ñ¥½¸´ÔÀÀ€‘í±¥Ù•MÑ…Ñ”€ôôô€‰±¥ÍÑ•¹¥¹œˆ€ü€‰Í…±”´ÄÀÔÍ¡…‘½Üµ½µÁ½Í•Èˆ€è€ˆ‰õôøñ¥µœÍÉŒôˆ½…ÍÍ•ÑÌ½Á•ÉÍ½¹…°µ…¤µ™±½Ü¹Á¹œˆ…±Ðôˆˆ±…ÍÍ9…µ”ô‰…‰Í½±ÕÑ”¥¹Í•Ð´À µ™Õ±°Üµ™Õ±°Í…±”µlÄ¸át½‰©•Ðµ½Ù•Èˆ€¼øñÍÁ…¸±…ÍÍ9…µ”õíÉ•±…Ñ¥Ù”É¥Í¥é”´ÈÀÁ±…”µ¥Ñ•µÌµ•¹Ñ•ÈÉ½Õ¹‘•µ™Õ±°‰œµÍÕÉ™…”µ•±•Ù…Ñ•¼äÀÑ•áÐµ…•¹Ðµ¡½Ù•ÈÍ¡…‘½ÜµÍ½™Ð€‘í±¥Ù•MÑ…Ñ”€ôôô€‰±¥ÍÑ•¹¥¹œˆ€ü€‰…¹¥µ…Ñ”µÁÕ±Í”ˆ€è€ˆ‰õôøñ5¥ŒÈ…É¥„µ¡¥‘‘•¸Í¥é”õìÌÁôÍÑÉ½­•]¥‘Ñ õìÄ¸Ùô€¼øð½ÍÁ…¸øð½‘¥Øø4(€€€€€€€€€€€€ñ È±…ÍÍ9…µ”ô‰µÐ´àÑ•áÐµlÈáÁát™½¹Ðµµ•‘¥Õ´ÑÉ…­¥¹œµl´À¸ÀÌÕ•µtˆùí±¥Ù•MÑ…Ñ”€ôôô€‰±¥ÍÑ•¹¥¹œˆ€ü€‰'Še´±¥ÍÑ•¹¥¹œˆ€è±¥Ù•MÑ…Ñ”€ôôô€‰½¹¹•Ñ¥¹œˆ€ü€‰½¹¹•Ñ¥¹ŸŠ˜ˆ€è€‰Q…±¬¥ÐÑ¡É½Õ ‰ôð½ Èø4(€€€€€€€€€€€€ñÀ±…ÍÍ9…µ”õíµÐ´Ìµ…àµÜµµÑ•áÐµÍ´±•…‘¥¹œ´Ø€‘í±¥Ù•MÑ…Ñ”€ôôô€‰•ÉÉ½Èˆ€ü€‰Ñ•áÐµ‘…¹•Èˆ€è€‰Ñ•áÐµÑ•áÐµÍ•½¹‘…Éä‰õôùíÉ•…±Ñ¥µ”€˜˜€…É•…±Ñ¥µ”¹½¹™¥ÕÉ•€˜˜±¥Ù•MÑ…Ñ”€ôôô€‰¥‘±”ˆ€ü€‰AP1¥Ù”¹••‘Ì„Í•ÉÙ•ÈµÍ¥‘”I•…±Ñ¥µ”É•‘•¹Ñ¥…°‰•™½É”Ñ¡¥ÌÁ¡½¹”…¸ÍÑ…ÉÐ„Ù½¥”½¹Ù•ÉÍ…Ñ¥½¸¸ˆ€è±¥Ù•5•ÍÍ…•ôð½Àø4(€€€€€€€€€€€í±¥Ù•…ÁÑ¥½¸€˜˜€ñÀ±…ÍÍ9…µ”ô‰µÐ´Ôµ…àµÜµ±œÉ½Õ¹‘•µ…É‰œµÍÕÉ™…”¼ÜÔÁà´ÐÁä´ÌÑ•áÐµÍ´±•…‘¥¹œ´ØÑ•áÐµÑ•áÐµÁÉ¥µ…Éäˆùí±¥Ù•…ÁÑ¥½¹ôð½Àùô4(€€€€€€€€€€€í±¥Ù•M…Ù•]…É¹¥¹œ€˜˜€ñÀ±…ÍÍ9…µ”ô‰µÐ´Ìµ…àµÜµµÑ•áÐµáÌ±•…‘¥¹œ´ÔÑ•áÐµÝ…É¹¥¹œˆùí±¥Ù•M…Ù•]…É¹¥¹ôð½Àùô4(€€€€€€€€€€€í±¥Ù•A±…å‰…­	±½­•€˜˜€ñ‰ÕÑÑ½¸ÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”ô‰‰ÕÑÑ½¸µÍ•½¹‘…ÉäµÐ´Ðˆ½¹±¥¬õì ¤€ôøÙ½¥É•ÍÕµ•1¥Ù•Õ‘¥¼ ¥ôùI•ÍÕµ”…Õ‘¥¼ð½‰ÕÑÑ½¸ùô4(€€€€€€€€€€€€ñÀ±…ÍÍ9…µ”ô‰µÐ´ÐÑ•áÐµáÌÑ•áÐµÑ•áÐµÑ•ÉÑ¥…ÉäˆùíÉ•…±Ñ¥µ”ü¹µ½‘•°ñð€‰I•…±Ñ¥µ”µ½‘•°‰ôƒ
Ü]•‰IQƒ
ÜíÁÉ½©•Ñôð½Àø4(€€€€€€€€€€€€ñÀ±…ÍÍ9…µ”ô‰µÐ´Èµ…àµÜµµÑ•áÐµlÄÅÁát±•…‘¥¹œ´ÔÑ•áÐµÑ•áÐµÑ•ÉÑ¥…Éäˆù½µÁ±•Ñ•1¥Ù”ÑÉ…¹ÍÉ¥ÁÑÌÍÑ…ä¥¸Ñ¡¥Ì½¹Ù•ÉÍ…Ñ¥½¸…¹…¸É•…Ñ”¥ÑÌÍ¡½ÉÐÑ¥Ñ±”¸Q¡•ä…É”¹½Ð…‘‘•Ñ¼5•µ½Éä…ÕÑ½µ…Ñ¥…±±ä¸ð½Àø4(€€€€€€€€€€€í±¥Ù•MÑ…Ñ”€ôôô€‰±¥ÍÑ•¹¥¹œˆñð±¥Ù•MÑ…Ñ”€ôôô€‰½¹¹•Ñ¥¹œˆ€ü€ñ‰ÕÑÑ½¸½¹±¥¬õì ¤€ôøÍÑ½Á1¥Ù” ¥ô±…ÍÍ9…µ”ô‰µÐ´à¥¹±¥¹”µ™±•àÍ¥é”´ÄØ¥Ñ•µÌµ•¹Ñ•È©ÕÍÑ¥™äµ•¹Ñ•ÈÉ½Õ¹‘•µ™Õ±°‰œµÑ•áÐµÁÉ¥µ…ÉäÑ•áÐµÍÕÉ™…”µ•±•Ù…Ñ•Í¡…‘½Üµ½µÁ½Í•Èˆ…É¥„µ±…‰•°ô‰¹±¥Ù”½¹Ù•ÉÍ…Ñ¥½¸ˆøñMÅÕ…É”…É¥„µ¡¥‘‘•¸Í¥é”õìÈÅô™¥±°ô‰ÕÉÉ•¹Ñ½±½Èˆ€¼øð½‰ÕÑÑ½¸ø€èÉ•…±Ñ¥µ”€˜˜€…É•…±Ñ¥µ”¹½¹™¥ÕÉ•€ü€ñ1¥¹¬¡É•˜ôˆ½Í•ÑÑ¥¹Ìµ½‰¥±”µÍ•ÑÑ¥¹Ìˆ±…ÍÍ9…µ”ô‰µÐ´à¥¹±¥¹”µ™±•àµ¥¸µ ´ÄÐ¥Ñ•µÌµ•¹Ñ•È©ÕÍÑ¥™äµ•¹Ñ•È…À´ÈÉ½Õ¹‘•µ™Õ±°‰œµÑ•áÐµÁÉ¥µ…ÉäÁà´ÜÑ•áÐµÍ´™½¹Ðµµ•‘¥Õ´Ñ•áÐµÍÕÉ™…”µ•±•Ù…Ñ•Í¡…‘½Üµ½µÁ½Í•Èˆøñ]É•¹ …É¥„µ¡¥‘‘•¸Í¥é”õìÄáô€¼ù½¹™¥ÕÉ”AP1¥Ù”ð½1¥¹¬ø€è€ñ‰ÕÑÑ½¸½¹±¥¬õì ¤€ôøÙ½¥ÍÑ…ÉÑ1¥Ù” ¥ô±…ÍÍ9…µ”ô‰µÐ´à¥¹±¥¹”µ™±•àµ¥¸µ ´ÄÐ¥Ñ•µÌµ•¹Ñ•È©ÕÍÑ¥™äµ•¹Ñ•È…À´ÈÉ½Õ¹‘•µ™Õ±°‰œµÑ•áÐµÁÉ¥µ…ÉäÁà´ÜÑ•áÐµÍ´™½¹Ðµµ•‘¥Õ´Ñ•áÐµÍÕÉ™…”µ•±•Ù…Ñ•Í¡…‘½Üµ½µÁ½Í•Èˆ‘¥Í…‰±•õì…É•…±Ñ¥µ•ôøñ5¥ŒÈ…É¥„µ¡¥‘‘•¸Í¥é”õìÄáô€¼ùíÉ•…±Ñ¥µ”€ü€‰MÑ…ÉÐAP1¥Ù”ˆ€è€‰¡•­¥¹œAP1¥Ù—Š˜‰ôð½‰ÕÑÑ½¸ùô4(€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€¥ô4(€€€€€€ð½Í•Ñ¥½¸ø4(4(€€€€€í¡¥ÍÑ½Éå=Á•¸€˜˜€ñ‘¥Ø±…ÍÍ9…µ”ô‰™¥á•¥¹Í•Ð´Àè´ÔÀˆøñ‰ÕÑÑ½¸±…ÍÍ9…µ”ô‰…‰Í½±ÕÑ”¥¹Í•Ð´À‰œµÑ•áÐµÁÉ¥µ…Éä¼ÈÀˆ½¹±¥¬õí±½Í•!¥ÍÑ½Éåô…É¥„µ±…‰•°ô‰±½Í”½¹Ù•ÉÍ…Ñ¥½¸¡¥ÍÑ½Éäˆ€¼øñ…Í¥‘”É•˜õí¡¥ÍÑ½Éå¥…±½I•™ôÉ½±”ô‰‘¥…±½œˆ…É¥„µµ½‘…°ô‰ÑÉÕ”ˆ…É¥„µ±…‰•°ô‰½¹Ù•ÉÍ…Ñ¥½¸¡¥ÍÑ½Éäˆ±…ÍÍ9…µ”ô‰…‰Í½±ÕÑ”¥¹Í•Ðµä´ÀÉ¥¡Ð´ÀÜµmµ¥¸ ÌÐÁÁà°äÁÙÜ¥t‰½É‘•Èµ°‰½É‘•Èµ±¥¹”‰œµÍÕÉ™…”µ•±•Ù…Ñ•À´ÐÍ¡…‘½Üµ½µÁ½Í•Èˆ½¹-•å½Ý¸õí¡…¹‘±•!¥ÍÑ½Éå-•åÍôøñ‘¥Ø±…ÍÍ9…µ”ô‰µˆ´Ð™±•à¥Ñ•µÌµ•¹Ñ•È©ÕÍÑ¥™äµ‰•ÑÝ••¸ˆøñ È±…ÍÍ9…µ”ô‰Ñ•áÐµ±œ™½¹Ðµµ•‘¥Õ´ˆù½¹Ù•ÉÍ…Ñ¥½¹Ìð½ Èøñ‰ÕÑÑ½¸±…ÍÍ9…µ”ô‰¥½¸µ‰ÕÑÑ½¸ˆ½¹±¥¬õí±½Í•!¥ÍÑ½Éåô…É¥„µ±…‰•°ô‰±½Í”½¹Ù•ÉÍ…Ñ¥½¸¡¥ÍÑ½Éäˆøñ`…É¥„µ¡¥‘‘•¸Í¥é”õìÈÁô€¼øð½‰ÕÑÑ½¸øð½‘¥Øùí¡¥ÍÑ½Éåôð½…Í¥‘”øð½‘¥Øùô4(4(€€€€€íµ•µ½ÉåQ…É•Ð€˜˜€ 4(€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰™¥á•¥¹Í•Ð´ÀèµlØÁt™±•à¥Ñ•µÌµ•¹©ÕÍÑ¥™äµ•¹Ñ•Èµé¥Ñ•µÌµ•¹Ñ•ÈµéÀ´Øˆø4(€€€€€€€€€€ñ‰ÕÑÑ½¸±…ÍÍ9…µ”ô‰…‰Í½±ÕÑ”¥¹Í•Ð´À‰œµÑ•áÐµÁÉ¥µ…Éä¼ÈÔˆ½¹±¥¬õí±½Í•5•µ½Éå¥…±½ô…É¥„µ±…‰•°ô‰±½Í”Í…Ù”Ñ¼µ•µ½Éäˆ€¼ø4(€€€€€€€€€€ñÍ•Ñ¥½¸É•˜õíµ•µ½Éå¥…±½I•™ôÉ½±”ô‰‘¥…±½œˆ…É¥„µµ½‘…°ô‰ÑÉÕ”ˆ…É¥„µ±…‰•±±•‘‰äô‰Í…Ù”µµ•µ½ÉäµÑ¥Ñ±”ˆ±…ÍÍ9…µ”ô‰É•±…Ñ¥Ù”Üµ™Õ±°É½Õ¹‘•µÐµlÈáÁát‰½É‘•È‰½É‘•Èµ±¥¹”‰œµÍÕÉ™…”µ•±•Ù…Ñ•Áà´ÔÁˆµmµ…à ÈÑÁà±•¹Ø¡Í…™”µ…É•„µ¥¹Í•Ðµ‰½ÑÑ½´¤¥tÁÐ´ÐÍ¡…‘½Üµ½µÁ½Í•Èµéµ…àµÜµ±œµéÉ½Õ¹‘•µ…ÉµéÀ´Øˆ½¹-•å½Ý¸õí¡…¹‘±•5•µ½Éå¥…±½-•å½Ý¹ôø4(€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰µàµ…ÕÑ¼µˆ´Ì ´ÄÜ´ÄÀÉ½Õ¹‘•µ™Õ±°‰œµ±¥¹”µÍÑÉ½¹œµé¡¥‘‘•¸ˆ…É¥„µ¡¥‘‘•¸€¼ø4(€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰™±•à¥Ñ•µÌµÍÑ…ÉÐ©ÕÍÑ¥™äµ‰•ÑÝ••¸…À´Ðˆø4(€€€€€€€€€€€€€€ñ‘¥ØøñÀ±…ÍÍ9…µ”ô‰•å•‰É½Üˆù1½¹œµÑ•É´µ•µ½Éäð½Àøñ È¥ô‰Í…Ù”µµ•µ½ÉäµÑ¥Ñ±”ˆ±…ÍÍ9…µ”ô‰µÐ´ÄÑ•áÐµá°™½¹Ðµµ•‘¥Õ´ÑÉ…­¥¹œµl´À¸ÀÉ•µtˆùM…Ù”Ý¡…Ðµ…ÑÑ•ÉÌð½ Èøð½‘¥Øø4(€€€€€€€€€€€€€€ñ‰ÕÑÑ½¸ÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”ô‰¥½¸µ‰ÕÑÑ½¸€µµÈ´È€µµÐ´Èˆ½¹±¥¬õí±½Í•5•µ½Éå¥…±½ô…É¥„µ±…‰•°ô‰±½Í”Í…Ù”Ñ¼µ•µ½Éäˆøñ`…É¥„µ¡¥‘‘•¸Í¥é”õìÈÁô€¼øð½‰ÕÑÑ½¸ø4(€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€ñÀ±…ÍÍ9…µ”ô‰µÐ´ÌÑ•áÐµÍ´±•…‘¥¹œ´ØÑ•áÐµÑ•áÐµÍ•½¹‘…Éäˆù=¹±äÑ¡¥ÌÉ•Ù¥•Ý•¹½Ñ”Ý¥±°‰”Í…Ù•¸Q¡”É•ÍÐ½˜Ñ¡”½¹Ù•ÉÍ…Ñ¥½¸ÍÑ…åÌ½ÕÐ½˜±½¹œµÑ•É´5•µ½Éä¸ð½Àø4(€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰ÍÉ½±±‰…ÈµÍÕ‰Ñ±”µÐ´Ô™±•à…À´È½Ù•É™±½Üµàµ…ÕÑ¼Áˆ´ÄˆÉ½±”ô‰É½ÕÀˆ…É¥„µ±…‰•°ô‰5•µ½ÉäÑåÁ”ˆø4(€€€€€€€€€€€€€ì¡l‰™…Ðˆ°€‰ÁÉ•™•É•¹”ˆ°€‰ÉÕ±”ˆ°€‰ÁÉ½©•Ð‰t…Ì5•µ½Éå-¥¹‘mt¤¹µ…À ¡¥Ñ•´¤€ôø€ñ‰ÕÑÑ½¸­•äõí¥Ñ•µôÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”õí¡¥Àµ¥¸µ ´ÄÄÍ¡É¥¹¬´À…Á¥Ñ…±¥é”€‘íµ•µ½Éå-¥¹€ôôô¥Ñ•´€ü€‰‰œµ…•¹ÐµÍ½™ÐÑ•áÐµ…•¹Ðµ¡½Ù•Èˆ€è€ˆ‰õô…É¥„µÁÉ•ÍÍ•õíµ•µ½Éå-¥¹€ôôô¥Ñ•µô½¹±¥¬õì ¤€ôøÍ•Ñ5•µ½Éå-¥¹¡¥Ñ•´¥ôùí¥Ñ•µôð½‰ÕÑÑ½¸ø¥ô4(€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€€€ñ±…‰•°±…ÍÍ9…µ”ô‰µÐ´Ð‰±½¬Ñ•áÐµáÌ™½¹Ðµµ•‘¥Õ´Ñ•áÐµÑ•áÐµÍ•½¹‘…Éäˆù5•µ½Éä¹½Ñ”ñÑ•áÑ…É•„±…ÍÍ9…µ”ô‰Ñ•áÑ…É•„µ™¥•±µÐ´Èµ¥¸µ ´ÌØÜµ™Õ±°É•Í¥é”µäÑ•áÐµlÄÕÁát±•…‘¥¹œ´ØˆÙ…±Õ”õíµ•µ½ÉåQ•áÑô½¹¡…¹”õì¡•Ù•¹Ð¤€ôøìÍ•Ñ5•µ½ÉåQ•áÐ¡•Ù•¹Ð¹Ñ…É•Ð¹Ù…±Õ”¤ì¥˜€¡µ•µ½ÉåMÑ…Ñ”€„ôô€‰¥‘±”ˆ¤Í•Ñ5•µ½ÉåMÑ…Ñ” ‰¥‘±”ˆ¤ìõô€¼øð½±…‰•°ø4(€€€€€€€€€€€€ñÀ±…ÍÍ9…µ”ô‰µÐ´ÈÑ•áÐµáÌÑ•áÐµÑ•áÐµÑ•ÉÑ¥…ÉäˆùAÉ½©•ÐèíÁÉ½©•ÑÌ¹™¥¹ ¡¥Ñ•´¤€ôø¥Ñ•´¹¥€ôôôÁÉ½©•Ð¤ü¹¹…µ”ñðÁÉ½©•Ñôƒ
ÜM½ÕÉ”èÑ¡¥Ì½¹Ù•ÉÍ…Ñ¥½¸ð½Àø4(€€€€€€€€€€€íµ•µ½ÉåMÑ…Ñ”€ôôô€‰•ÉÉ½Èˆ€˜˜€ñÀ±…ÍÍ9…µ”ô‰µÐ´ÌÑ•áÐµÍ´Ñ•áÐµ‘…¹•ÈˆÉ½±”ô‰…±•ÉÐˆùQ¡¥Ì¹½Ñ”½Õ±¹½Ð‰”Í…Ù•¸¡•¬Ñ¡”±½…°A$…¹ÑÉä……¥¸¸ð½Àùô4(€€€€€€€€€€€€ñÀ±…ÍÍ9…µ”ô‰ÍÈµ½¹±äˆÉ½±”ô‰ÍÑ…ÑÕÌˆ…É¥„µ±¥Ù”ô‰Á½±¥Ñ”ˆùíµ•µ½ÉåMÑ…Ñ”€ôôô€‰Í…Ù•ˆ€ü€‰5•µ½ÉäÍ…Ù•¸ˆ€èµ•µ½ÉåMÑ…Ñ”€ôôô€‰Í…Ù¥¹œˆ€ü€‰M…Ù¥¹œµ•µ½Éä¸ˆ€è€ˆ‰ôð½Àø4(€€€€€€€€€€€€ñ‘¥Ø±…ÍÍ9…µ”ô‰µÐ´Ô™±•à…À´Ìˆø4(€€€€€€€€€€€€€€ñ‰ÕÑÑ½¸ÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”ô‰‰ÕÑÑ½¸µÍ•½¹‘…Éä™±•à´Äˆ½¹±¥¬õí±½Í•5•µ½Éå¥…±½ôù…¹•°ð½‰ÕÑÑ½¸ø4(€€€€€€€€€€€€€€ñ‰ÕÑÑ½¸ÑåÁ”ô‰‰ÕÑÑ½¸ˆ±…ÍÍ9…µ”ô‰‰ÕÑÑ½¸µÁÉ¥µ…Éä™±•à´Äˆ½¹±¥¬õì ¤€ôøÙ½¥Í…Ù•5•µ½Éä ¥ô‘¥Í…‰±•õì…µ•µ½ÉåQ•áÐ¹ÑÉ¥´ ¤ñðµ•µ½ÉåMÑ…Ñ”€ôôô€‰Í…Ù¥¹œˆñðµ•µ½ÉåMÑ…Ñ”€ôôô€‰Í…Ù•‰ôùíµ•µ½ÉåMÑ…Ñ”€ôôô€‰Í…Ù•ˆ€ü€ðøñ¡•¬…É¥„µ¡¥‘‘•¸Í¥é”õìÄÝô€¼ùM…Ù•ð¼ø€èµ•µ½ÉåMÑ…Ñ”€ôôô€‰Í…Ù¥¹œˆ€ü€‰M…Ù¥¹ŸŠ˜ˆ€è€‰M…Ù”µ•µ½Éä‰ôð½‰ÕÑÑ½¸ø4(€€€€€€€€€€€€ð½‘¥Øø4(€€€€€€€€€€ð½Í•Ñ¥½¸ø4(€€€€€€€€ð½‘¥Øø4(€€€€€€¥ô4(€€€€ð½‘¥Øø4(€€¤ì4)ô4(