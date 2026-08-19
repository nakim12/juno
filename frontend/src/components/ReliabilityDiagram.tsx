"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { CalibrationReliability } from "@/types";

const SIZE = 300;
const PAD_L = 40;
const PAD_B = 36;
const PAD_T = 14;
const PAD_R = 16;

const x = (p: number) => PAD_L + p * (SIZE - PAD_R - PAD_L);
const y = (a: number) => SIZE - PAD_B - a * (SIZE - PAD_B - PAD_T);

const TICKS = [0, 0.25, 0.5, 0.75, 1];

/** Marker radius scaled by how much of the sample sits in a bin. */
function radius(share: number) {
  return 5 + Math.sqrt(share) * 11;
}

/** Sit the label above its marker, flipping below when it would clip the top. */
function labelY(acc: number, share: number) {
  const above = y(acc) - radius(share) - 6;
  return above < PAD_T + 6 ? y(acc) + radius(share) + 11 : above;
}

/**
 * Reliability diagram: stated confidence on x, observed accuracy on y. Points on
 * the dashed diagonal are perfectly calibrated; above it the agent is
 * underconfident (right more often than it claims), below it overconfident.
 */
export function ReliabilityDiagram({ data }: { data: CalibrationReliability }) {
  const reduced = useReducedMotion();
  const bins = [...data.per_label].sort((a, b) => a.mapped_prob - b.mapped_prob);

  const curve = bins.map((b) => `${x(b.mapped_prob)},${y(b.empirical_acc)}`).join(" ");
  const overall = data.mean_confidence - data.mean_accuracy;
  const verdict =
    overall < -0.05 ? "underconfident" : overall > 0.05 ? "overconfident" : "well calibrated";

  return (
    <div className="grid gap-8 md:grid-cols-[minmax(0,320px)_1fr] md:items-center">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="w-full max-w-[320px]"
        role="img"
        aria-label={`Reliability diagram: the agent is ${verdict}. ${bins
          .map(
            (b) =>
              `${b.label} confidence is scored ${Math.round(
                b.mapped_prob * 100
              )} percent and is correct ${Math.round(b.empirical_acc * 100)} percent of the time`
          )
          .join("; ")}.`}
      >
        {TICKS.map((t) => (
          <g key={t}>
            <line
              x1={x(t)}
              y1={PAD_T}
              x2={x(t)}
              y2={SIZE - PAD_B}
              stroke="hsl(var(--border))"
              strokeWidth="1"
              opacity="0.35"
            />
            <line
              x1={PAD_L}
              y1={y(t)}
              x2={SIZE - PAD_R}
              y2={y(t)}
              stroke="hsl(var(--border))"
              strokeWidth="1"
              opacity="0.35"
            />
            <text
              x={x(t)}
              y={SIZE - PAD_B + 15}
              textAnchor="middle"
              className="fill-[hsl(var(--muted-foreground))] text-[9px]"
            >
              {t}
            </text>
            <text
              x={PAD_L - 8}
              y={y(t) + 3}
              textAnchor="end"
              className="fill-[hsl(var(--muted-foreground))] text-[9px]"
            >
              {t}
            </text>
          </g>
        ))}

        {/* Perfect calibration. Fades rather than draws: animating pathLength
            drives stroke-dasharray internally, which would erase the dashes. */}
        <motion.line
          x1={x(0)}
          y1={y(0)}
          x2={x(1)}
          y2={y(1)}
          stroke="hsl(var(--muted-foreground))"
          strokeWidth="1.5"
          strokeDasharray="5 5"
          initial={reduced ? false : { opacity: 0 }}
          whileInView={{ opacity: 0.6 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
        />

        {/* Gap from the diagonal, one drop line per bin */}
        {bins.map((b, i) => (
          <motion.line
            key={`gap-${b.label}`}
            x1={x(b.mapped_prob)}
            y1={y(b.mapped_prob)}
            x2={x(b.mapped_prob)}
            y2={y(b.empirical_acc)}
            stroke="hsl(var(--accent))"
            strokeWidth="1"
            strokeDasharray="2 3"
            initial={reduced ? false : { opacity: 0 }}
            whileInView={{ opacity: 0.55 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.4, delay: 0.7 + i * 0.12 }}
          />
        ))}

        <motion.polyline
          points={curve}
          fill="none"
          stroke="hsl(var(--accent))"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={reduced ? false : { pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.9, delay: 0.5, ease: [0.22, 1, 0.36, 1] }}
        />

        {bins.map((b, i) => (
          <motion.g
            key={b.label}
            initial={reduced ? false : { opacity: 0, scale: 0.4 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.4, delay: 0.9 + i * 0.12 }}
            style={{ transformOrigin: `${x(b.mapped_prob)}px ${y(b.empirical_acc)}px` }}
          >
            <circle
              cx={x(b.mapped_prob)}
              cy={y(b.empirical_acc)}
              r={radius(b.share)}
              fill="hsl(var(--accent) / 0.22)"
              stroke="hsl(var(--accent))"
              strokeWidth="1.5"
            />
            <text
              x={x(b.mapped_prob)}
              y={labelY(b.empirical_acc, b.share)}
              textAnchor="middle"
              className="fill-[hsl(var(--foreground))] text-[9px] font-medium"
            >
              {b.label}
            </text>
          </motion.g>
        ))}

        <text
          x={(PAD_L + SIZE - PAD_R) / 2}
          y={SIZE - 4}
          textAnchor="middle"
          className="fill-[hsl(var(--muted-foreground))] text-[9px]"
        >
          stated confidence
        </text>
        <text
          x={-(PAD_T + SIZE - PAD_B) / 2}
          y={11}
          textAnchor="middle"
          transform="rotate(-90)"
          className="fill-[hsl(var(--muted-foreground))] text-[9px]"
        >
          observed accuracy
        </text>
      </svg>

      <div>
        <div className="overflow-hidden rounded-xl border border-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface">
              <tr className="mono text-[0.65rem] uppercase tracking-wider text-muted-foreground">
                <th className="px-3 py-2 font-normal">confidence</th>
                <th className="px-3 py-2 text-right font-normal">n</th>
                <th className="px-3 py-2 text-right font-normal">scored</th>
                <th className="px-3 py-2 text-right font-normal">actual</th>
                <th className="px-3 py-2 text-right font-normal">gap</th>
              </tr>
            </thead>
            <tbody>
              {[...data.per_label].map((b) => (
                <tr key={b.label} className="border-t border-border">
                  <td className="px-3 py-2 font-medium">{b.label}</td>
                  <td className="mono px-3 py-2 text-right text-muted-foreground">{b.n}</td>
                  <td className="mono px-3 py-2 text-right text-muted-foreground">
                    {b.mapped_prob.toFixed(2)}
                  </td>
                  <td className="mono px-3 py-2 text-right">{b.empirical_acc.toFixed(2)}</td>
                  <td
                    className={`mono px-3 py-2 text-right ${
                      Math.abs(b.gap) <= 0.07
                        ? "text-success"
                        : b.gap > 0
                          ? "text-warning"
                          : "text-accent"
                    }`}
                  >
                    {b.gap > 0 ? "+" : ""}
                    {b.gap.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mono mt-3 text-xs leading-relaxed text-muted-foreground">
          {data.n_points} per-channel observations · mean confidence{" "}
          {data.mean_confidence.toFixed(2)} vs. accuracy {data.mean_accuracy.toFixed(2)} ·{" "}
          <span className="text-foreground">{verdict}</span>
        </p>
      </div>
    </div>
  );
}

export default ReliabilityDiagram;
