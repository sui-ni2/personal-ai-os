export type SseEvent = {
  id: string;
  type: "context" | "routing" | "message" | "tool_start" | "tool_result" | "error" | "done";
  status: "started" | "running" | "succeeded" | "failed" | "cancelled" | "interrupted" | "outcome_unknown" | "retry_safe" | "retry_requires_confirmation";
  conversation_id?: string;
  tool?: string;
  duration_ms?: number;
  payload: Record<string, unknown>;
  created_at: string;
};

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export async function streamSse(
  path: string,
  body: unknown,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) throw new Error(`Stream failed (${response.status})`);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";
    for (const frame of frames) {
      const data = frame.split("\n").find((line) => line.startsWith("data: "));
      if (data) onEvent(JSON.parse(data.slice(6)) as SseEvent);
    }
    if (done) break;
  }
}
