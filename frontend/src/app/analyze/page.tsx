"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listSamples, loadSample } from "@/lib/api";
import { ReportView } from "@/components/ReportView";
import { ChatPanel } from "@/components/ChatPanel";
import type { AnalysisReport, SampleInfo } from "@/types";

export default function Analyze() {
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSamples()
      .then(setSamples)
      .catch(() => setError("Could not reach the backend. Is it running on :8000?"));
  }, []);

  async function onLoad(id: string) {
    setLoading(true);
    setError(null);
    try {
      const { session_id, report } = await loadSample(id);
      setSessionId(session_id);
      setReport(report);
    } catch {
      setError("Failed to load sample.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <Link
            href="/"
            className="mono text-xs text-muted-foreground transition hover:text-foreground"
          >
            ← back
          </Link>
          <h1 className="mono mt-2 text-2xl font-semibold">
            juno<span className="text-accent">.</span>
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            An agentic copilot that interprets Marketing Mix Model outputs and answers
            your questions with grounded reasoning and explicit confidence.
          </p>
        </div>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-[hsl(var(--error)/0.4)] bg-[hsl(var(--error)/0.14)] p-3 text-sm text-error">
          {error}
        </div>
      )}

      <section className="mb-10">
        <div className="eyebrow mb-4">Load a sample MMM output</div>
        <div className="flex flex-wrap gap-3">
          {samples.map((s) => (
            <button
              key={s.id}
              onClick={() => onLoad(s.id)}
              disabled={loading}
              className="card px-4 py-3 text-left text-sm transition hover:border-accent disabled:opacity-50"
            >
              <div className="font-medium">{s.name}</div>
              <div className="mono mt-1 text-xs text-muted-foreground">
                {s.n_channels} channels · {s.data_span_weeks ?? "?"} weeks · {s.model_type}
              </div>
            </button>
          ))}
          {samples.length === 0 && !error && (
            <p className="text-sm text-muted-foreground">Loading samples…</p>
          )}
        </div>
      </section>

      {loading && <p className="mono text-sm text-muted-foreground">Analyzing…</p>}

      {report && sessionId && (
        <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <ReportView report={report} />
          </div>
          <div className="lg:sticky lg:top-10 lg:h-[80vh]">
            <h2 className="mb-3 text-lg font-semibold">Chat</h2>
            <div className="h-[calc(100%-2.5rem)] rounded-xl border border-border p-4">
              <ChatPanel sessionId={sessionId} />
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
