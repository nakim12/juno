"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import type { AnalysisReport, Citation, Confidence } from "@/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.16, delayChildren: 0.1 } },
};

// A slightly quicker rhythm for lists nested inside a section, so cards cascade
// visibly without dragging the whole report out too long.
const listContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
};

/** A confidence badge that "settles" into place — a small spring on mount. */
function SettlingBadge({ level }: { level: Confidence }) {
  const reduced = useReducedMotion();
  if (reduced) return <ConfidenceBadge level={level} />;
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 420, damping: 18, delay: 0.15 }}
      className="inline-block"
    >
      <ConfidenceBadge level={level} />
    </motion.span>
  );
}

function citationLabel(c: Citation): string {
  if (c.source_type === "knowledge_base") {
    // chunk ids look like "saturation::0" — show the readable topic.
    const topic = c.reference.split("::")[0].replace(/_/g, " ");
    return `KB · ${topic}`;
  }
  return `model · ${c.reference}`;
}

function Citations({ items }: { items: Citation[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {items.map((c, i) => (
        <span
          key={i}
          title={c.snippet ?? c.reference}
          className={`mono rounded border px-1.5 py-0.5 text-[0.62rem] ${
            c.source_type === "knowledge_base"
              ? "border-accent/40 bg-accent/10 text-accent"
              : "border-border bg-muted text-muted-foreground"
          }`}
        >
          {citationLabel(c)}
        </span>
      ))}
    </div>
  );
}

export function ReportView({ report }: { report: AnalysisReport }) {
  return (
    <motion.div
      className="space-y-6"
      variants={container}
      initial="hidden"
      animate="show"
    >
      <motion.section variants={item}>
        <h2 className="mb-2 text-lg font-semibold">Overview</h2>
        <p className="text-sm leading-relaxed opacity-90">{report.overview}</p>
      </motion.section>

      <motion.section variants={item}>
        <h2 className="mb-3 text-lg font-semibold">Per-Channel Analysis</h2>
        <motion.div className="space-y-3" variants={listContainer}>
          {report.per_channel.map((c) => (
            <motion.div
              key={c.channel_name}
              variants={item}
              className="rounded-lg border border-border bg-[hsl(var(--muted))] p-4"
            >
              <div className="mb-1 flex items-center justify-between">
                <h3 className="font-medium">{c.channel_name}</h3>
                <SettlingBadge level={c.confidence} />
              </div>
              <p className="text-sm opacity-90">{c.interpretation}</p>
              <p className="mt-1 text-xs italic opacity-60">{c.confidence_reasoning}</p>
              <Citations items={c.citations} />
            </motion.div>
          ))}
        </motion.div>
      </motion.section>

      {report.structural_risks.length > 0 && (
        <motion.section variants={item}>
          <h2 className="mb-3 text-lg font-semibold">Structural Risks</h2>
          <motion.ul className="space-y-2" variants={listContainer}>
            {report.structural_risks.map((r, i) => (
              <motion.li
                key={i}
                variants={item}
                className="rounded-lg border border-border p-3 text-sm"
              >
                <span className="font-medium">{r.title}</span> — {r.description}
                <Citations items={r.citations} />
              </motion.li>
            ))}
          </motion.ul>
        </motion.section>
      )}

      <motion.section variants={item}>
        <h2 className="mb-3 text-lg font-semibold">Recommendations</h2>
        <motion.div className="space-y-3" variants={listContainer}>
          {report.recommendations.map((rec, i) => (
            <motion.div
              key={i}
              variants={item}
              className="rounded-lg border border-border p-4"
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium">{rec.action}</span>
                <SettlingBadge level={rec.confidence} />
              </div>
              <p className="text-sm opacity-90">{rec.rationale}</p>
              {rec.dependencies.length > 0 && (
                <p className="mt-1 text-xs opacity-60">
                  Depends on: {rec.dependencies.join(", ")}
                </p>
              )}
              <Citations items={rec.citations} />
            </motion.div>
          ))}
        </motion.div>
      </motion.section>

      {report.knowledge_sources && report.knowledge_sources.length > 0 && (
        <motion.section variants={item}>
          <h2 className="mb-1 text-lg font-semibold">Knowledge base sources consulted</h2>
          <p className="mb-3 text-xs text-muted-foreground">
            Methodology chunks retrieved and provided to the agent to ground its
            reasoning.
          </p>
          <div className="space-y-2">
            {report.knowledge_sources.map((s) => (
              <details
                key={s.chunk_id}
                className="rounded-lg border border-border bg-muted/40 p-3"
              >
                <summary className="cursor-pointer text-sm font-medium">
                  <span className="mono text-xs text-accent">{s.topic ?? s.chunk_id}</span>
                </summary>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                  {s.snippet}
                </p>
              </details>
            ))}
          </div>
        </motion.section>
      )}

      <motion.p variants={item} className="text-xs opacity-40">
        Generated by {report.metadata.agent_model} · prompt{" "}
        {report.metadata.prompt_version}
      </motion.p>
    </motion.div>
  );
}
