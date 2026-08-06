"use client";

import { useState } from "react";
import { streamChat } from "@/lib/api";
import type { ChatTurn, KnowledgeSource } from "@/types";

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
        onSources: (sources: KnowledgeSource[]) =>
          setTurns((t) => {
            const copy = [...t];
            copy[assistantIndex] = { ...copy[assistantIndex], sources };
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
                  ? "bg-[hsl(var(--accent))] font-medium text-[hsl(var(--background))]"
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
            {turn.role === "assistant" && turn.sources && turn.sources.length > 0 && (
              <ChatSources sources={turn.sources} />
            )}
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
          className="rounded-lg bg-[hsl(var(--accent))] px-4 py-2 text-sm font-medium text-[hsl(var(--background))] disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}

function ChatSources({ sources }: { sources: KnowledgeSource[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1.5 text-left">
      <button
        onClick={() => setOpen((o) => !o)}
        className="mono text-[0.7rem] text-muted-foreground transition hover:text-accent"
      >
        {open ? "▾" : "▸"} {sources.length} source{sources.length > 1 ? "s" : ""} consulted
      </button>
      {open && (
        <ul className="mt-2 space-y-2 border-l border-border pl-3">
          {sources.map((s) => (
            <li key={s.chunk_id} className="text-xs">
              <span className="mono text-accent">{s.topic ?? s.chunk_id}</span>
              {s.snippet && (
                <p className="mt-0.5 text-muted-foreground">{s.snippet}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
