import type {
  AnalysisReport,
  EvaluationSummary,
  KnowledgeSource,
  SampleInfo,
} from "@/types";

// Base URL for API calls. The browser hits the backend directly rather than
// going through Next's /api rewrite, because that proxy BUFFERS streaming
// responses — the SSE analysis and chat streams then arrive in one dump at the
// end instead of building progressively, which is the whole demo.
//
// The deployed backend origin is committed rather than left purely to
// NEXT_PUBLIC_API_BASE. That env var is inlined at build time, so a missing or
// mis-scoped value can't be detected at runtime and fails *silently*: the app
// still works, but every stream is buffered. Since there is exactly one public
// backend, hardcoding it as the production default makes the good path the
// default and the env var an override (useful for forks and staging).
//
// Changing the backend host means editing this line. That's the deliberate
// trade: an obvious, greppable constant over an invisible degradation.
const PROD_API_BASE = "https://juno-backend-wa9w.onrender.com";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : PROD_API_BASE);

const api = (path: string) => `${API_BASE}${path}`;

// --- Bring-your-own-key -----------------------------------------------------
// The public demo answers a curated set of questions from a pre-computed cache
// and never spends the owner's API credit. Anyone who wants live generation
// supplies their own key, which is held in sessionStorage (cleared when the tab
// closes) and sent per request. It is never persisted server-side.

const KEY_STORAGE = "juno.anthropic-key";
const KEY_HEADER = "X-Anthropic-Api-Key";

export function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(KEY_STORAGE);
}

export function setApiKey(key: string | null): void {
  if (typeof window === "undefined") return;
  if (key) window.sessionStorage.setItem(KEY_STORAGE, key);
  else window.sessionStorage.removeItem(KEY_STORAGE);
}

function keyHeaders(): Record<string, string> {
  const key = getApiKey();
  return key ? { [KEY_HEADER]: key } : {};
}

/** Thrown when an action needs live generation the demo won't pay for. */
export class NeedsApiKeyError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NeedsApiKeyError";
  }
}

export interface ChatCapabilities {
  questions: string[];
  free_text_enabled: boolean;
  demo_mode: boolean;
}

export async function getChatCapabilities(sessionId: string): Promise<ChatCapabilities> {
  const res = await fetch(api(`/api/chat/${sessionId}/suggestions`), {
    headers: keyHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load chat suggestions");
  return res.json();
}

/** Parses an uploaded model without interpreting it — free, no LLM call. */
export async function parseUpload(
  mmmOutput: unknown
): Promise<{ session_id: string; summary: AnalysisSummaryEvent }> {
  const res = await fetch(api("/api/parse"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mmmOutput),
  });
  if (!res.ok) {
    throw new Error(await readErrorDetail(res, "That file couldn't be parsed."));
  }
  return res.json();
}

/**
 * Fire-and-forget ping to wake a sleeping backend.
 *
 * Render's free tier spins the service down after inactivity and takes ~50s to
 * cold start. Calling this when someone lands on the site means the container is
 * usually warm by the time they click through to the demo, instead of the wait
 * landing on the first thing they actually try to do.
 */
export function warmBackend(): void {
  fetch(api("/health"), { cache: "no-store" }).catch(() => {
    // A failed warmup is not worth surfacing; the real request will report it.
  });
}

export async function getEvaluationSummary(): Promise<EvaluationSummary> {
  const res = await fetch(api("/api/evaluation/summary"), { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load evaluation summary");
  return res.json();
}

export async function listSamples(): Promise<SampleInfo[]> {
  const res = await fetch(api("/api/samples"), { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load samples");
  return res.json();
}

export async function loadSample(
  id: string
): Promise<{ session_id: string; report: AnalysisReport }> {
  const res = await fetch(api(`/api/samples/${id}/load`), { method: "POST" });
  if (!res.ok) throw new Error("Failed to load sample");
  return res.json();
}

export async function analyzeUpload(
  mmmOutput: unknown
): Promise<{ session_id: string; report: AnalysisReport }> {
  const res = await fetch(api("/api/analyze"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mmmOutput),
  });
  if (!res.ok) throw new Error("Failed to analyze upload");
  return res.json();
}

export interface AnalysisSummaryEvent {
  model_type: string;
  n_channels: number;
  channels: string[];
  detected_issues: string[];
}

export interface AnalysisStreamHandlers {
  onSummary?: (summary: AnalysisSummaryEvent) => void;
  onSources?: (sources: KnowledgeSource[]) => void;
  onProgress?: (chars: number) => void;
  onReport: (sessionId: string, report: AnalysisReport) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

/** Iterates SSE events from a fetch Response body, invoking cb per event. */
async function readSSE(
  res: Response,
  cb: (eventType: string | undefined, data: unknown) => void
): Promise<void> {
  if (!res.body) throw new Error("No response body");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const evt of events) {
      const lines = evt.split("\n");
      const eventType = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
      const dataLine = lines.find((l) => l.startsWith("data:"))?.slice(5).trim();
      if (!dataLine) continue;
      cb(eventType, JSON.parse(dataLine));
    }
  }
}

function dispatchAnalysisEvent(
  handlers: AnalysisStreamHandlers,
  eventType: string | undefined,
  data: any
) {
  if (eventType === "summary") handlers.onSummary?.(data);
  else if (eventType === "sources") handlers.onSources?.(data.sources);
  else if (eventType === "progress") handlers.onProgress?.(data.chars);
  else if (eventType === "report") handlers.onReport(data.session_id, data.report);
  else if (eventType === "error") handlers.onError?.(data.message);
  else if (eventType === "done") handlers.onDone?.();
}

/** Streams the initial analysis for a sample, emitting staged progress events. */
export async function streamLoadSample(
  id: string,
  handlers: AnalysisStreamHandlers
): Promise<void> {
  const res = await fetch(api(`/api/samples/${id}/load/stream`), { method: "POST" });
  if (!res.ok) throw new Error("Failed to load sample");
  await readSSE(res, (t, d) => dispatchAnalysisEvent(handlers, t, d));
}

/** Turn a FastAPI error body into a readable message (handles 422 validation). */
async function readErrorDetail(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // Pydantic validation errors: [{loc: [...], msg: "..."}]
      return detail
        .map((e: { loc?: (string | number)[]; msg?: string }) => {
          const field = (e.loc ?? []).filter((p) => p !== "body").join(".");
          return field ? `${field}: ${e.msg}` : e.msg;
        })
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    /* non-JSON body */
  }
  return fallback;
}

/** Streams the initial analysis for an uploaded MMM output. */
export async function streamAnalyzeUpload(
  mmmOutput: unknown,
  handlers: AnalysisStreamHandlers
): Promise<void> {
  const res = await fetch(api("/api/analyze/stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...keyHeaders() },
    body: JSON.stringify(mmmOutput),
  });
  if (res.status === 402) {
    throw new NeedsApiKeyError(
      await readErrorDetail(res, "Live analysis needs your own API key.")
    );
  }
  if (!res.ok) {
    throw new Error(
      await readErrorDetail(res, "The MMM output could not be analyzed.")
    );
  }
  await readSSE(res, (t, d) => dispatchAnalysisEvent(handlers, t, d));
}

/**
 * Streams a chat response over Server-Sent Events. Calls onToken for each token
 * and onMeta once with the classified question type.
 */
export async function streamChat(
  sessionId: string,
  message: string,
  handlers: {
    onMeta?: (questionType: string) => void;
    onSources?: (sources: KnowledgeSource[]) => void;
    onToken: (text: string) => void;
    onError?: (message: string) => void;
    onDone?: () => void;
  }
): Promise<void> {
  const res = await fetch(api("/api/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...keyHeaders() },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (res.status === 402) {
    throw new NeedsApiKeyError(
      await readErrorDetail(res, "Only the suggested questions are pre-answered.")
    );
  }
  if (!res.ok) {
    throw new Error(
      await readErrorDetail(res, "Chat request failed. Please try again.")
    );
  }

  await readSSE(res, (eventType, data: any) => {
    if (eventType === "meta") handlers.onMeta?.(data.question_type);
    else if (eventType === "sources") handlers.onSources?.(data.sources);
    else if (eventType === "token") handlers.onToken(data.text);
    else if (eventType === "error") handlers.onError?.(data.message);
    else if (eventType === "done") handlers.onDone?.();
  });
}
