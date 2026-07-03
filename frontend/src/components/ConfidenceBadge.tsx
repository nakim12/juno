import type { Confidence } from "@/types";

const STYLES: Record<Confidence, string> = {
  high: "bg-green-100 text-green-800 border-green-300",
  medium: "bg-amber-100 text-amber-800 border-amber-300",
  low: "bg-red-100 text-red-800 border-red-300",
};

export function ConfidenceBadge({ level }: { level: Confidence }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${STYLES[level]}`}
    >
      {level} confidence
    </span>
  );
}
