"use client";

import { useRef, useState } from "react";

const EXAMPLE = {
  metadata: { model_type: "bayesian", data_span_weeks: 52 },
  channels: [
    {
      name: "Search",
      spend_weekly: [12000, 12500, 11800, 13000],
      roi_point: 3.2,
      roi_ci: [2.8, 3.6],
      adstock_decay: 0.4,
      saturation_params: { half_saturation: 40000, shape: 1.1 },
      contribution_pct: 0.45,
    },
    {
      name: "Social",
      spend_weekly: [8000, 8200, 7900, 8100],
      roi_point: 1.9,
      roi_ci: [1.2, 2.6],
      adstock_decay: 0.6,
      saturation_params: { half_saturation: 25000, shape: 1.0 },
      contribution_pct: 0.3,
    },
  ],
  model_diagnostics: { r_squared: 0.86, mape: 0.12 },
};

export function UploadPanel({
  onAnalyze,
  disabled,
}: {
  onAnalyze: (data: unknown) => void;
  disabled: boolean;
}) {
  const [text, setText] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function loadFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result ?? ""));
    reader.onerror = () => setLocalError("Could not read that file.");
    reader.readAsText(file);
  }

  function submit() {
    setLocalError(null);
    if (!text.trim()) {
      setLocalError("Paste your MMM output JSON or upload a .json file first.");
      return;
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      setLocalError(
        `Invalid JSON: ${e instanceof Error ? e.message : "could not parse"}`
      );
      return;
    }
    onAnalyze(parsed);
  }

  return (
    <div className="card p-5">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <button
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          className="rounded-lg border border-border px-3 py-1.5 text-sm transition hover:border-accent disabled:opacity-50"
        >
          Upload .json
        </button>
        <button
          onClick={() => {
            setText(JSON.stringify(EXAMPLE, null, 2));
            setLocalError(null);
          }}
          disabled={disabled}
          className="mono text-xs text-muted-foreground transition hover:text-accent disabled:opacity-50"
        >
          load example
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) loadFile(f);
            e.target.value = "";
          }}
        />
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        spellCheck={false}
        placeholder="Paste your MMM output JSON here…"
        className="mono h-48 w-full resize-y rounded-lg border border-border bg-transparent p-3 text-xs outline-none focus:border-accent disabled:opacity-50"
      />

      {localError && (
        <p className="mt-2 text-sm text-error">{localError}</p>
      )}

      <div className="mt-3 flex items-center justify-between gap-3">
        <details className="text-xs text-muted-foreground">
          <summary className="mono cursor-pointer transition hover:text-foreground">
            expected format
          </summary>
          <pre className="mono mt-2 max-h-56 overflow-auto rounded-lg border border-border bg-[hsl(var(--surface))] p-3 text-[0.7rem] leading-relaxed">
{JSON.stringify(EXAMPLE, null, 2)}
          </pre>
        </details>

        <button
          onClick={submit}
          disabled={disabled}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-[hsl(var(--background))] transition hover:opacity-90 disabled:opacity-50"
        >
          Analyze my output
        </button>
      </div>
    </div>
  );
}
