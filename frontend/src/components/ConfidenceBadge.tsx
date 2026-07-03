import type { Confidence } from "@/types";

const STYLES: Record<Confidence, string> = {
  high: "text-green-400 border-green-400/30 bg-green-400/10",
  medium: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  low: "text-red-400 border-red-400/30 bg-red-400/10",
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
