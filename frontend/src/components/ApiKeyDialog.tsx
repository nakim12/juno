"use client";

import { useState } from "react";
import { setApiKey } from "@/lib/api";

/**
 * Lets a visitor supply their own Anthropic key to unlock live generation.
 *
 * The demo is free to run because answers are pre-computed; anything beyond the
 * curated questions bills someone, and that someone shouldn't be the person
 * hosting it. The key lives in sessionStorage — gone when the tab closes — and
 * is sent per request without ever being stored server-side.
 */
export function ApiKeyDialog({
  open,
  onClose,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [value, setValue] = useState("");
  const [touched, setTouched] = useState(false);

  if (!open) return null;

  const looksValid = value.trim().startsWith("sk-ant-");

  function save() {
    setTouched(true);
    if (!looksValid) return;
    setApiKey(value.trim());
    setValue("");
    setTouched(false);
    onSaved();
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-background/80 p-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="api-key-title"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md space-y-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <h2 id="api-key-title" className="text-lg font-semibold">
            Use your own API key
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
            The suggested questions are pre-answered and free. To ask anything else, or
            to analyze your own upload, add an Anthropic key — requests are billed to
            you, not to this demo.
          </p>
        </div>

        <div>
          <label htmlFor="api-key" className="eyebrow mb-1.5 block">
            Anthropic API key
          </label>
          <input
            id="api-key"
            type="password"
            autoComplete="off"
            spellCheck={false}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
            placeholder="sk-ant-…"
            className="mono w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none focus:border-accent"
          />
          {touched && !looksValid && (
            <p className="mt-1.5 text-xs text-error">
              That doesn&apos;t look like an Anthropic key — they start with{" "}
              <code className="mono">sk-ant-</code>.
            </p>
          )}
        </div>

        <p className="text-xs leading-relaxed text-muted-foreground">
          Stored in this tab only (sessionStorage) and sent with each request. It is
          never written to the server.{" "}
          <a
            href="https://console.anthropic.com/settings/keys"
            target="_blank"
            rel="noreferrer"
            className="text-accent underline underline-offset-2"
          >
            Get a key
          </a>
          .
        </p>

        <div className="flex justify-end gap-2 pt-1">
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm transition hover:border-accent"
          >
            Cancel
          </button>
          <button
            onClick={save}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-[hsl(var(--background))] transition hover:opacity-90"
          >
            Unlock live mode
          </button>
        </div>
      </div>
    </div>
  );
}

export default ApiKeyDialog;
