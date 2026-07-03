"use client";

import { useState } from "react";
import { streamChat } from "@/lib/api";
import type { ChatTurn } from "@/types";

export function ChatPanel({ sessionId }: { sessionId: string }) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const message = input.trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { role: "user", content: message }]);

    const assistantIndex = turns.length + 1;
    setTurns((t) => [...t, { role: "assistant", content: "" }]);

    try {
      await streamChat(sessionId, message, {
        onMeta: (questionType) =>
          setTurns((t) => {
            const copy = [...t];
            copy[assistantIndex] = {
              ...copy[assistantIndex],
              questionType: questionType as ChatTurn["questionType"],
            };
            return copy;
          }),
        onToken: (text) =>
          setTurns((t) => {
            const copy = [...t];
            copy[assistantIndex] = {
              ...copy[assistantIndex],
              content: copy[assistantIndex].content + text,
            };
            return copy;
          }),
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-1">
        {turns.length === 0 && (
          <p className="text-sm opacity-50">
            Ask about ROI, saturation, budget shifts, or how confident you should be.
          </p>
        )}
        {turns.map((turn, i) => (
          <div
            key={i}
            className={turn.role === "user" ? "text-right" : "text-left"}
          >
            <div
              className={`inline-block max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                turn.role === "user"
                  ? "bg-[hsl(var(--accent))] text-white"
                  : "border border-border bg-[hsl(var(--muted))]"
              }`}
            >
              {turn.questionType && (
                <span className="mb-1 block text-[10px] uppercase tracking-wide opacity-50">
                  {turn.questionType}
                </span>
              )}
              {turn.content || "…"}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex gap-2 border-t border-border pt-3">
        <input
          className="flex-1 rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none"
          placeholder="Ask Juno about this model…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={busy}
        />
        <button
          onClick={send}
          disabled={busy}
          className="rounded-lg bg-[hsl(var(--accent))] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
