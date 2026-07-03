import type { Confidence } from "@/types";

const STYLES: Record<Confidence, string> = {
  high: "text-success border-[hsl(var(--success)/0.4)] bg-[hsl(var(--success)/0.14)]",
  medium: "text-warning border-[hsl(var(--warning)/0.4)] bg-[hsl(var(--warning)/0.14)]",
  low: "text-error border-[hsl(var(--error)/0.4)] bg-[hsl(var(--error)/0.14)]",
};

export function ConfidenceBadge({ level }: { level: Confidence }) {
  return (
    <span
      className={`mono inline-flex items-center rounded-full border px-2 py-0.5 text-[0.65rem] ${STYLES[level]}`}
    >
      {level} confidence
    </span>
  );
}
