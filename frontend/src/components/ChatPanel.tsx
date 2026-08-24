"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getApiKey,
  getChatCapabilities,
  NeedsApiKeyError,
  setApiKey,
  streamChat,
  type ChatCapabilities,
} from "@/lib/api";
import { ApiKeyDialog } from "@/components/ApiKeyDialog";
import type { ChatTurn, KnowledgeSource } from "@/types";

export function ChatPanel({ sessionId }: { sessionId: string }) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [caps, setCaps] = useState<ChatCapabilities | null>(null);
  const [asked, setAsked] = useState<string[]>([]);
  const [keyDialogOpen, setKeyDialogOpen] = useState(false);
  const [hasKey, setHasKey] = useState(false);

  const refreshCaps = useCallback(() => {
    getChatCapabilities(sessionId)
      .then(setCaps)
      .catch(() => setCaps(null));
  }, [sessionId]);

  useEffect(() => {
    setHasKey(Boolean(getApiKey()));
    refreshCaps();
  }, [refreshCaps]);

  const remaining = (caps?.questions ?? []).filter((q) => !asked.includes(q));
  const freeTextEnabled = caps?.free_text_enabled ?? true;

  async function ask(message: string) {
    if (!message || busy) return;
    setError(null);
    setInput("");
    setBusy(true);
    setAsked((a) => [...a, message]);
    setTurns((t) => [...t, { role: "user", content: message }]);

    const assistantIndex = turns.length + 1;
    setTurns((t) => [...t, { role: "assistant", content: "" }]);

    const patch = (fields: Partial<ChatTurn>) =>
      setTurns((t) => {
        const copy = [...t];
        copy[assistantIndex] = { ...copy[assistantIndex], ...fields };
        return copy;
      });

    let streamFailed = false;

    try {
      await streamChat(sessionId, message, {
        onMeta: (questionType) =>
          patch({ questionType: questionType as ChatTurn["questionType"] }),
        onSources: (sources: KnowledgeSource[]) => patch({ sources }),
        onError: (msg) => {
          streamFailed = true;
          setError(msg);
        },
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
      // The stream can report a provider failure and still close cleanly; drop
      // the bubble it never filled.
      if (streamFailed) setTurns((t) => t.slice(0, assistantIndex));
    } catch (e) {
      // Drop the empty assistant bubble; without this a failed request leaves a
      // "…" placeholder that never resolves.
      setTurns((t) => t.slice(0, assistantIndex));
      if (e instanceof NeedsApiKeyError) {
        setError(e.message);
        setKeyDialogOpen(true);
      } else {
        setError(e instanceof Error ? e.message : "Something went wrong.");
      }
    } finally {
      setBusy(false);
    }
  }

  function onKeySaved() {
    setHasKey(true);
    setError(null);
    refreshCaps();
  }

  function clearKey() {
    setApiKey(null);
    setHasKey(false);
    refreshCaps();
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
          <div key={i} className={turn.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
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

      {remaining.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {remaining.map((q) => (
            <button
              key={q}
              onClick={() => ask(q)}
              disabled={busy}
              className="rounded-full border border-border bg-muted/60 px-3 py-1.5 text-xs text-muted-foreground transition hover:border-accent hover:text-foreground disabled:opacity-40"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {error && (
        <p className="mt-3 rounded-lg border border-[hsl(var(--error)/0.4)] bg-[hsl(var(--error)/0.14)] px-3 py-2 text-xs text-error">
          {error}
        </p>
      )}

      <div className="mt-3 border-t border-border pt-3">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none disabled:opacity-50"
            placeholder={
              freeTextEnabled
                ? "Ask Juno about this model…"
                : "Pick a suggested question, or add a key to ask your own"
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask(input.trim())}
            disabled={busy || !freeTextEnabled}
          />
          <button
            onClick={() => ask(input.trim())}
            disabled={busy || !freeTextEnabled}
            className="rounded-lg bg-[hsl(var(--accent))] px-4 py-2 text-sm font-medium text-[hsl(var(--background))] disabled:opacity-50"
          >
            Send
          </button>
        </div>

        <p className="mono mt-2 text-[0.7rem] text-muted-foreground">
          {hasKey ? (
            <>
              Live mode — billed to your key.{" "}
              <button onClick={clearKey} className="text-accent hover:underline">
                remove key
              </button>
            </>
          ) : (
            <>
              Free demo — the suggested answers are pre-computed.{" "}
              <button
                onClick={() => setKeyDialogOpen(true)}
                className="text-accent hover:underline"
              >
                use your own API key
              </button>{" "}
              to ask anything.
            </>
          )}
        </p>
      </div>

      <ApiKeyDialog
        open={keyDialogOpen}
        onClose={() => setKeyDialogOpen(false)}
        onSaved={onKeySaved}
      />
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
              {s.snippet && <p className="mt-0.5 text-muted-foreground">{s.snippet}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
