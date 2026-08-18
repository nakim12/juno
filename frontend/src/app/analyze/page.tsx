"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listSamples,
  streamLoadSample,
  streamAnalyzeUpload,
  type AnalysisStreamHandlers,
  type AnalysisSummaryEvent,
} from "@/lib/api";
import { ReportView } from "@/components/ReportView";
import { ChatPanel } from "@/components/ChatPanel";
import { UploadPanel } from "@/components/UploadPanel";
import { AnalysisProgress, type ProgressState } from "@/components/AnalysisProgress";
import { InnerNav } from "@/components/motion/InnerNav";
import { AmbientBackdrop } from "@/components/motion/AmbientBackdrop";
import type { AnalysisReport, KnowledgeSource, SampleInfo } from "@/types";

const EMPTY_PROGRESS: ProgressState = {
  summary: null,
  sources: null,
  chars: 0,
  reportReady: false,
};

export default function Analyze() {
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [samplesLoading, setSamplesLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<ProgressState>(EMPTY_PROGRESS);
  const [error, setError] = useState<string | null>(null);

  const loadSamples = useCallback(() => {
    setSamplesLoading(true);
    setOffline(false);
    listSamples()
      .then((s) => setSamples(s))
      .catch(() => setOffline(true))
      .finally(() => setSamplesLoading(false));
  }, []);

  useEffect(() => {
    loadSamples();
  }, [loadSamples]);

  async function runAnalysis(
    starter: (handlers: AnalysisStreamHandlers) => Promise<void>,
    fallbackError: string
  ) {
    setLoading(true);
    setError(null);
    setReport(null);
    setSessionId(null);
    setProgress(EMPTY_PROGRESS);
    try {
      await starter({
        onSummary: (summary: AnalysisSummaryEvent) =>
          setProgress((p) => ({ ...p, summary })),
        onSources: (sources: KnowledgeSource[]) =>
          setProgress((p) => ({ ...p, sources })),
        onProgress: (chars: number) => setProgress((p) => ({ ...p, chars })),
        onReport: (session_id: string, rpt: AnalysisReport) => {
          setProgress((p) => ({ ...p, reportReady: true }));
          setSessionId(session_id);
          setReport(rpt);
        },
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : fallbackError);
    } finally {
      setLoading(false);
    }
  }

  const onLoad = (id: string) =>
    runAnalysis((h) => streamLoadSample(id, h), "Failed to load sample.");

  const onUpload = (data: unknown) =>
    runAnalysis((h) => streamAnalyzeUpload(data, h), "Failed to analyze upload.");

  return (
    <div className="relative min-h-screen overflow-hidden">
      <AmbientBackdrop />
      <InnerNav active="analyze" />
      <main className="relative mx-auto max-w-6xl px-6 py-12">
      <header className="mb-10">
        <div className="eyebrow mb-3">the copilot</div>
        <h1 className="display text-3xl font-semibold sm:text-4xl">
          Analyze an <span className="gradient-text">MMM output</span>
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          An agentic copilot that interprets Marketing Mix Model outputs and answers
          your questions with grounded reasoning and explicit confidence.
        </p>
      </header>

      {error && (
        <div className="mb-6 flex items-start justify-between gap-3 rounded-lg border border-[hsl(var(--error)/0.4)] bg-[hsl(var(--error)/0.14)] p-3 text-sm text-error">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="mono shrink-0 text-xs opacity-70 transition hover:opacity-100"
          >
            dismiss
          </button>
        </div>
      )}

      {offline ? (
        <div className="card flex flex-col items-start gap-4 p-8">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-error" />
            <span className="eyebrow">Backend offline</span>
          </div>
          <h2 className="text-xl font-semibold">Can&apos;t reach the Juno API</h2>
          <p className="max-w-lg text-sm text-muted-foreground">
            The frontend proxies to the backend on <code className="mono text-accent">:8000</code>.
            Start it with{" "}
            <code className="mono text-accent">uvicorn app.main:app --port 8000</code> from the{" "}
            <code className="mono">backend/</code> directory, then retry.
          </p>
          <button
            onClick={loadSamples}
            disabled={samplesLoading}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-[hsl(var(--background))] transition hover:opacity-90 disabled:opacity-50"
          >
            {samplesLoading ? "Retrying…" : "Retry connection"}
          </button>
        </div>
      ) : (
        <>
          <section className="mb-10">
            <div className="eyebrow mb-4">Load a sample MMM output</div>
            <div className="flex flex-wrap gap-3">
              {samplesLoading &&
                [0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="shimmer h-[4.25rem] w-52 rounded-xl border border-border"
                  />
                ))}
              {!samplesLoading &&
                samples.map((s) => (
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
            </div>
          </section>

          <section className="mb-10">
            <div className="eyebrow mb-4">…or analyze your own MMM output</div>
            <UploadPanel onAnalyze={onUpload} disabled={loading} />
          </section>
        </>
      )}

      {loading && !report && <AnalysisProgress progress={progress} />}

      {!offline && !loading && !report && (
        <div className="rounded-xl border border-dashed border-border bg-surface/40 p-8 text-center">
          <p className="text-sm text-muted-foreground">
            Pick a sample or upload your own MMM output to see a grounded, streamed
            analysis and start chatting about it.
          </p>
        </div>
      )}

      {report && sessionId && (
        <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <ReportView report={report} />
          </div>
          <div className="h-[70vh] lg:sticky lg:top-24 lg:h-[80vh]">
            <h2 className="mb-3 text-lg font-semibold">Chat</h2>
            <div className="h-[calc(100%-2.5rem)] rounded-xl border border-border p-4">
              <ChatPanel sessionId={sessionId} />
            </div>
          </div>
        </div>
      )}
      </main>
    </div>
  );
}
