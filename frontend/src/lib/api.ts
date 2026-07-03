import type { AnalysisReport, SampleInfo } from "@/types";

// Requests are proxied to the FastAPI backend via next.config rewrites.
export async function listSamples(): Promise<SampleInfo[]> {
  const res = await fetch("/api/samples", { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load samples");
  return res.json();
}

export async function loadSample(
  id: string
): Promise<{ session_id: string; report: AnalysisReport }> {
  const res = await fetch(`/api/samples/${id}/load`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to load sample");
  return res.json();
}

export async function analyzeUpload(
  mmmOutput: unknown
): Promise<{ session_id: string; report: AnalysisReport }> {
  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mmmOutput),
  });
  if (!res.ok) throw new Error("Failed to analyze upload");
  return res.json();
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
    onToken: (text: string) => void;
    onDone?: () => void;
  }
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
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
      const data = JSON.parse(dataLine);
      if (eventType === "meta") handlers.onMeta?.(data.question_type);
      else if (eventType === "token") handlers.onToken(data.text);
      else if (eventType === "done") handlers.onDone?.();
    }
  }
}
