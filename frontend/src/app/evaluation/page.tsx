"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { getEvaluationSummary } from "@/lib/api";
import { CountUp } from "@/components/motion/CountUp";
import { LaurelWreath } from "@/components/motion/LaurelWreath";
import { Reveal } from "@/components/motion/Reveal";
import type { EvaluationSummary } from "@/types";

const DIMENSION_ORDER = [
  "accuracy",
  "calibration_ece",
  "groundedness",
  "actionability",
  "failure_mode_recall",
  "hallucination_rate",
] as const;

function parseTarget(target: string): { op: string; value: number } {
  const m = target.match(/([<>]=?)\s*([\d.]+)/);
  return m ? { op: m[1], value: parseFloat(m[2]) } : { op: ">", value: 0 };
}

function passes(value: number, target: string): boolean {
  const { op, value: t } = parseTarget(target);
  return op.startsWith(">") ? value > t : value < t;
}

function MetricValue({ metricKey, value }: { metricKey: string; value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-2xl font-semibold text-muted-foreground">—</span>;
  }
  if (metricKey === "actionability") {
    return (
      <span className="text-2xl font-semibold">
        <CountUp to={value} decimals={2} suffix=" / 5" />
      </span>
    );
  }
  return (
    <span className="text-2xl font-semibold">
      <CountUp to={value} decimals={3} />
    </span>
  );
}

export default function EvaluationPage() {
  const [data, setData] = useState<EvaluationSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    getEvaluationSummary()
      .then(setData)
      .catch(() => setError("Could not load evaluation data. Is the backend running?"));
  }, []);

  const run = data?.run;

  return (
    <div className="relative overflow-hidden">
      <nav className="sticky top-0 z-20 border-b border-border/70 bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="mono flex items-center gap-2 text-sm font-medium">
            <LaurelWreath className="h-7 w-7 text-accent" />
            juno<span className="text-accent">.</span>
          </Link>
          <div className="mono flex items-center gap-6 text-xs">
            <Link href="/" className="text-muted-foreground transition hover:text-foreground">
              home
            </Link>
            <Link
              href="/analyze"
              className="rounded-md border border-border bg-muted px-3 py-1.5 font-medium text-foreground transition hover:border-accent"
            >
              try the demo →
            </Link>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-5xl px-6 py-16">
        <Reveal>
          <div className="eyebrow mb-4">Trust &amp; Evaluation</div>
          <h1 className="display max-w-3xl text-4xl font-semibold sm:text-5xl">
            We measure whether the advice can be{" "}
            <span className="gradient-text">trusted</span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Most AI copilots are plausible-sounding demos with no proof the advice is good.
            Juno ships with an evaluation framework: a benchmark of ground-truth MMM scenarios,
            an independent LLM-as-judge, and a validation step that checks the judge itself.
          </p>
        </Reveal>

        {error && (
          <div className="mt-8 rounded-lg border border-[hsl(var(--error)/0.4)] bg-[hsl(var(--error)/0.14)] p-3 text-sm text-error">
            {error}
          </div>
        )}

        {!data && !error && (
          <p className="mono mt-10 text-sm text-muted-foreground">Loading metrics…</p>
        )}

        {data && !data.available && (
          <div className="mt-10 rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
            No benchmark run has been recorded yet. Run the suite with
            <code className="mono mx-1 text-accent">python -m app.evaluation.run_eval</code>
            to populate these metrics.
          </div>
        )}

        {run && data && (
          <>
            {/* Metric cards */}
            <section className="mt-14">
              <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-xl font-semibold">Latest benchmark</h2>
                <span className="mono text-xs text-muted-foreground">
                  {run.n_cases} cases · agent {run.agent_model} · judge{" "}
                  {run.judge_model ?? "—"} · {new Date(run.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-3">
                {DIMENSION_ORDER.map((key) => {
                  const meta = data.targets[key];
                  const value = run[key as keyof typeof run] as number | null;
                  const pending = value === null || value === undefined;
                  const ok = !pending && passes(value as number, meta.target);
                  return (
                    <div key={key} className="bg-background p-5">
                      <div className="text-xs text-muted-foreground">{meta.label}</div>
                      <div className="mt-2 flex items-baseline gap-2">
                        <MetricValue metricKey={key} value={value} />
                        <span
                          className={`mono text-[0.65rem] ${
                            pending
                              ? "text-muted-foreground"
                              : ok
                                ? "text-success"
                                : "text-warning"
                          }`}
                        >
                          {pending ? "pending" : ok ? "on target" : "off"}
                        </span>
                      </div>
                      <div className="mono mt-1 text-[0.7rem] text-muted-foreground">
                        target {meta.target}
                      </div>
                    </div>
                  );
                })}
              </div>
              {run.weighted_total !== null && run.weighted_total !== undefined && (
                <div className="mt-4 flex items-center gap-3 rounded-xl border border-border bg-surface px-5 py-4">
                  <span className="text-sm text-muted-foreground">Weighted composite</span>
                  <CountUp
                    className="mono text-lg font-semibold text-accent"
                    to={run.weighted_total}
                    decimals={3}
                  />
                </div>
              )}
              {data.note && (
                <p className="mono mt-3 text-xs text-muted-foreground">{data.note}</p>
              )}
            </section>

            {/* Six dimensions explainer */}
            <section className="mt-16">
              <h2 className="text-xl font-semibold">How each dimension is measured</h2>
              <div className="mt-5 grid gap-px overflow-hidden rounded-2xl border border-border bg-border md:grid-cols-2">
                {[
                  ["Accuracy", "Spearman rank correlation between the agent's channel ROI ranking and the ground-truth ranking. Deterministic."],
                  ["Calibration", "Expected Calibration Error — do the agent's confidence levels match how often it's actually right? Deterministic."],
                  ["Groundedness", "Does every claim trace back to the model output or a cited source? Judged by an independent model."],
                  ["Actionability", "Is the recommendation specific and executable, not 'consider testing'? Judged 0–5."],
                  ["Failure-mode recall", "Of the structural risks we injected (multicollinearity, saturation, wide CIs…), how many did the agent flag? Deterministic."],
                  ["Hallucination", "Rate of claims unsupported by the output or sources. Judged."],
                ].map(([label, body]) => (
                  <div key={label} className="bg-background p-6">
                    <h3 className="text-sm font-semibold text-accent">{label}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Scenario breakdown */}
            {run.scenario_breakdown?.recall_by_failure_mode && (
              <section className="mt-16">
                <h2 className="text-xl font-semibold">Failure-mode recall by type</h2>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  Where the agent catches injected structural risks — and where it doesn&apos;t.
                </p>
                <div className="mt-5 space-y-2">
                  {Object.entries(run.scenario_breakdown.recall_by_failure_mode).map(
                    ([mode, recall]) => (
                      <div key={mode} className="flex items-center gap-3">
                        <span
                          title={mode}
                          className="mono w-28 shrink-0 truncate text-xs text-muted-foreground sm:w-56"
                        >
                          {mode}
                        </span>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface">
                          <motion.div
                            className="h-full rounded-full bg-accent"
                            initial={reduced ? false : { width: 0 }}
                            whileInView={{ width: `${Math.round(recall * 100)}%` }}
                            viewport={{ once: true, margin: "-40px" }}
                            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
                          />
                        </div>
                        <span className="mono w-12 shrink-0 text-right text-xs">
                          <CountUp to={recall} decimals={2} />
                        </span>
                      </div>
                    )
                  )}
                </div>
              </section>
            )}

            {/* Judge validation */}
            {data.judge_validation && (
              <section className="mt-16">
                <h2 className="text-xl font-semibold">Validating the judge</h2>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  &quot;LLM-as-judge&quot; can look rigorous while being noise. We measure the
                  judge&apos;s <strong>test-retest reliability</strong>: re-scoring the same
                  outputs {data.judge_validation.k_repetitions}× and checking consistency
                  (weighted Cohen&apos;s κ).
                </p>
                <div className="mt-5 flex items-center gap-3 rounded-xl border border-border bg-surface px-5 py-4">
                  <span className="text-sm text-muted-foreground">Overall test-retest κ</span>
                  <CountUp
                    className="mono text-lg font-semibold text-accent"
                    to={data.judge_validation.overall_test_retest_kappa}
                    decimals={3}
                  />
                  <span className="mono text-xs text-muted-foreground">
                    (&gt; 0.8 near-perfect)
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-3">
                  {Object.entries(data.judge_validation.per_dimension).map(([dim, s]) => (
                    <div key={dim} className="bg-background p-4">
                      <div className="text-xs text-muted-foreground">{dim}</div>
                      <div className="mono mt-1 text-lg font-semibold">
                        <CountUp to={s.test_retest_kappa} decimals={2} />
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mono mt-3 text-xs text-muted-foreground">
                  Reliability ≠ validity: a consistent judge can be consistently wrong. A
                  human-labelling harness (Cohen&apos;s κ vs. hand scores) is wired for the
                  validity check.
                </p>
              </section>
            )}

            {/* Failure catalog */}
            {data.failures && (
              <section className="mt-16">
                <h2 className="text-xl font-semibold">Failure-mode catalog</h2>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  Low-scoring responses are logged and categorized into a growing taxonomy —
                  {" "}the artifact real LLM-evals teams build.
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <div className="card px-5 py-4">
                    <CountUp
                      className="mono text-2xl font-semibold text-accent"
                      to={data.failures.total}
                    />
                    <div className="mt-1 text-xs text-muted-foreground">logged entries</div>
                  </div>
                  {Object.entries(data.failures.by_category).map(([cat, n]) => (
                    <div key={cat} className="card px-5 py-4">
                      <CountUp className="mono text-2xl font-semibold" to={n} />
                      <div className="mt-1 text-xs text-muted-foreground">{cat}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        <section className="mt-20">
          <div className="card hero-glow p-10 text-center">
            <h2 className="display text-3xl font-semibold">See the reasoning for yourself</h2>
            <p className="mx-auto mt-3 max-w-lg text-muted-foreground">
              Load a model and watch Juno interpret it — grounded, cited, and confidence-tagged.
            </p>
            <Link
              href="/analyze"
              className="mt-8 inline-block rounded-xl bg-gradient-to-br from-accent to-accent-2 px-7 py-3.5 text-sm font-semibold text-background shadow-lg shadow-accent/25 transition hover:opacity-90"
            >
              Launch the demo →
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
