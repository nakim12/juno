import type { AnalysisSummaryEvent } from "@/lib/api";
import type { KnowledgeSource } from "@/types";

export interface ProgressState {
  summary: AnalysisSummaryEvent | null;
  sources: KnowledgeSource[] | null;
  chars: number;
  reportReady: boolean;
}

type StepStatus = "pending" | "active" | "done";

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "done") {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[hsl(var(--success)/0.16)] text-[0.7rem] text-success">
        ✓
      </span>
    );
  }
  if (status === "active") {
    return (
      <span className="relative flex h-5 w-5 items-center justify-center">
        <span className="absolute h-3 w-3 animate-ping rounded-full bg-[hsl(var(--accent)/0.5)]" />
        <span className="h-2 w-2 rounded-full bg-accent" />
      </span>
    );
  }
  return (
    <span className="flex h-5 w-5 items-center justify-center">
      <span className="h-2 w-2 rounded-full border border-border" />
    </span>
  );
}

function Chip({
  children,
  index = 0,
}: {
  children: React.ReactNode;
  index?: number;
}) {
  return (
    <span
      className="pop-in mono rounded-full border border-border bg-surface px-2 py-0.5 text-[0.65rem] text-muted-foreground"
      style={{ animationDelay: `${index * 0.08}s` }}
    >
      {children}
    </span>
  );
}

export function AnalysisProgress({ progress }: { progress: ProgressState }) {
  const { summary, sources, chars, reportReady } = progress;

  const parseStatus: StepStatus = summary ? "done" : "active";
  const retrieveStatus: StepStatus = sources
    ? "done"
    : summary
      ? "active"
      : "pending";
  const generateStatus: StepStatus = reportReady
    ? "done"
    : sources
      ? "active"
      : "pending";

  return (
    <div className="card relative max-w-xl overflow-hidden p-6">
      {generateStatus === "active" && <div className="scan-line pointer-events-none" />}
      <div className="eyebrow mb-5">Analyzing MMM output</div>

      <ol className="space-y-5">
        <li className="flex gap-3">
          <StepIcon status={parseStatus} />
          <div className="flex-1">
            <div className="text-sm font-medium">Parsing model output</div>
            {summary ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Chip index={0}>{summary.n_channels} channels</Chip>
                <Chip index={1}>{summary.model_type}</Chip>
                {summary.detected_issues.map((code, i) => (
                  <Chip key={code} index={2 + i}>
                    {code}
                  </Chip>
                ))}
              </div>
            ) : (
              <div className="mono mt-1 text-xs text-muted-foreground">
                reading channels and detecting issues…
              </div>
            )}
          </div>
        </li>

        <li className="flex gap-3">
          <StepIcon status={retrieveStatus} />
          <div className="flex-1">
            <div className="text-sm font-medium">Consulting knowledge base</div>
            {sources ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Chip index={0}>{sources.length} sources</Chip>
                {sources.slice(0, 6).map((s, i) => (
                  <Chip key={s.chunk_id} index={1 + i}>
                    {s.topic ?? s.chunk_id}
                  </Chip>
                ))}
              </div>
            ) : (
              <div className="mono mt-1 text-xs text-muted-foreground">
                {summary ? "retrieving grounded methodology…" : "waiting…"}
              </div>
            )}
          </div>
        </li>

        <li className="flex gap-3">
          <StepIcon status={generateStatus} />
          <div className="flex-1">
            <div className="text-sm font-medium">Generating grounded analysis</div>
            <div className="mono mt-1 text-xs text-muted-foreground">
              {generateStatus === "done"
                ? "complete — rendering report…"
                : generateStatus === "active"
                  ? `writing report — ${chars.toLocaleString()} characters so far`
                  : "waiting…"}
            </div>
            {generateStatus === "active" && (
              <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-surface">
                <div className="h-full w-1/3 animate-pulse rounded-full bg-accent" />
              </div>
            )}
          </div>
        </li>
      </ol>

      <p className="mono mt-6 text-[0.7rem] text-muted-foreground">
        The model writes the full report in one grounded pass; this typically takes
        under two minutes.
      </p>
    </div>
  );
}
