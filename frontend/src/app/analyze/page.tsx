"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  listSamples,
  NeedsApiKeyError,
  parseUpload,
  streamLoadSample,
  streamAnalyzeUpload,
  type AnalysisStreamHandlers,
  type AnalysisSummaryEvent,
} from "@/lib/api";
import { ApiKeyDialog } from "@/components/ApiKeyDialog";
import { ReportView } from "@/components/ReportView";
import { ChatPanel } from "@/components/ChatPanel";
import { UploadPanel } from "@/components/UploadPanel";
import { AnalysisProgress, type ProgressState } from "@/components/AnalysisProgress";
import { InnerNav } from "@/components/motion/InnerNav";
import { AmbientBackdrop } from "@/components/motion/AmbientBackdrop";
import type { AnalysisReport, KnowledgeSource, SampleInfo } from "@/types";

// Backoff for waking a sleeping backend. Sums to ~58s, which covers the free
// hosting tier's cold start (~50s) without hammering a host that's genuinely down.
const WAKE_RETRY_DELAYS_MS = [3000, 5000, 8000, 12000, 15000, 15000];

const IS_DEV = process.env.NODE_ENV === "development";

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
  const [wakeAttempt, setWakeAttempt] = useState(0);
  const [gaveUp, setGaveUp] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<ProgressState>(EMPTY_PROGRESS);
  const [error, setError] = useState<string | null>(null);
  const [parsedOnly, setParsedOnly] = useState<AnalysisSummaryEvent | null>(null);
  const [keyDialogOpen, setKeyDialogOpen] = useState(false);

  const connect = useCallback(async () => {
    setSamplesLoading(true);
    try {
      setSamples(await listSamples());
      setOffline(false);
      return true;
    } catch {
      setOffline(true);
      return false;
    } finally {
      setSamplesLoading(false);
    }
  }, []);

  useEffect(() => {
    void connect();
  }, [connect]);

  // A failed first call is usually the host cold-starting, not a real outage,
  // so keep retrying quietly for about a minute before showing a dead end.
  useEffect(() => {
    if (!offline || gaveUp) return;
    if (wakeAttempt >= WAKE_RETRY_DELAYS_MS.length) {
      setGaveUp(true);
      return;
    }
    const timer = setTimeout(async () => {
      if (!(await connect())) setWakeAttempt((n) => n + 1);
    }, WAKE_RETRY_DELAYS_MS[wakeAttempt]);
    return () => clearTimeout(timer);
  }, [offline, wakeAttempt, gaveUp, connect]);

  function retryNow() {
    setGaveUp(false);
    setWakeAttempt(0);
    void connect();
  }

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
      // Callers handle this one: an upload that needs a key can still be parsed.
      if (e instanceof NeedsApiKeyError) throw e;
      setError(e instanceof Error ? e.message : fallbackError);
    } finally {
      setLoading(false);
    }
  }

  const onLoad = (id: string) =>
    runAnalysis((h) => streamLoadSample(id, h), "Failed to load sample.");

  async function onUpload(data: unknown) {
    setParsedOnly(null);
    try {
      await runAnalysis(
        (h) => streamAnalyzeUpload(data, h),
        "Failed to analyze upload."
      );
    } catch (e) {
      if (!(e instanceof NeedsApiKeyError)) throw e;
      // The demo won't pay to interpret an arbitrary upload, but parsing is
      // deterministic and free — so still show the visitor their own model.
      setError(null);
      try {
        const { summary } = await parseUpload(data);
        setParsedOnly(summary);
      } catch (parseErr) {
        setError(
          parseErr instanceof Error ? parseErr.message : "That file couldn't be parsed."
        );
      }
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <AmbientBackdrop />
      <InnerNav active="analyze" />
      <main id="main" tabIndex={-1} className="relative mx-auto max-w-6xl px-6 py-12">
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
            <span
              className={`h-2 w-2 rounded-full ${gaveUp ? "bg-error" : "bg-warning animate-pulse"}`}
            />
            <span className="eyebrow">{gaveUp ? "Backend offline" : "Waking the server"}</span>
          </div>

          {gaveUp ? (
            <>
              <h2 className="text-xl font-semibold">Can&apos;t reach the Juno API</h2>
              <p className="max-w-lg text-sm text-muted-foreground">
                {IS_DEV ? (
                  <>
                    Start the backend with{" "}
                    <code className="mono text-accent">uvicorn app.main:app --port 8000</code> from
                    the <code className="mono">backend/</code> directory, then retry.
                  </>
                ) : (
                  <>
                    The demo server isn&apos;t responding. It may still be starting up — try again
                    in a moment. The{" "}
                    <Link href="/evaluation" className="text-accent underline underline-offset-2">
                      evaluation results
                    </Link>{" "}
                    are served statically and work regardless.
                  </>
                )}
              </p>
            </>
          ) : (
            <>
              <h2 className="text-xl font-semibold">Starting the demo server</h2>
              <p className="max-w-lg text-sm text-muted-foreground">
                The backend sleeps when nobody&apos;s using it and takes up to a minute to wake.
                This retries on its own — no need to refresh.
              </p>
            </>
          )}

          <button
            onClick={retryNow}
            disabled={samplesLoading}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-[hsl(var(--background))] transition hover:opacity-90 disabled:opacity-50"
          >
            {samplesLoading ? "Connecting…" : "Retry now"}
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

      {parsedOnly && !report && (
        <div className="card space-y-4 p-6">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-accent" />
            <span className="eyebrow">Parsed — interpretation locked</span>
          </div>
          <h2 className="text-xl font-semibold">We read your model</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="model type" value={parsedOnly.model_type} />
            <Stat label="channels" value={String(parsedOnly.n_channels)} />
            <Stat
              label="structural flags"
              value={String(parsedOnly.detected_issues.length)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {parsedOnly.channels.map((c) => (
              <span
                key={c}
                className="mono rounded-full border border-border bg-muted/60 px-3 py-1 text-xs"
              >
                {c}
              </span>
            ))}
            {parsedOnly.detected_issues.map((issue) => (
              <span
                key={issue}
                className="mono rounded-full border border-[hsl(var(--warning)/0.5)] bg-[hsl(var(--warning)/0.12)] px-3 py-1 text-xs text-warning"
              >
                {issue}
              </span>
            ))}
          </div>
          <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Parsing is deterministic, so it runs free. Writing the interpretation takes
            a live model call, which this demo won&apos;t bill to its owner — add your
            own Anthropic key to generate the full report, or load a bundled sample to
            see one that&apos;s already been generated.
          </p>
          <button
            onClick={() => setKeyDialogOpen(true)}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-[hsl(var(--background))] transition hover:opacity-90"
          >
            Add your API key
          </button>
        </div>
      )}

      {!offline && !loading && !report && !parsedOnly && (
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

      <ApiKeyDialog
        open={keyDialogOpen}
        onClose={() => setKeyDialogOpen(false)}
        onSaved={() => setKeyDialogOpen(false)}
      />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/40 px-4 py-3">
      <div className="eyebrow mb-1">{label}</div>
      <div className="mono text-sm text-foreground">{value}</div>
    </div>
  );
}
