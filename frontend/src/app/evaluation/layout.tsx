import type { Metadata } from "next";

// The page itself is a client component and can't export metadata.
export const metadata: Metadata = {
  title: "Evaluation",
  description:
    "How Juno is measured: a ground-truth MMM benchmark, an independent LLM-as-judge, and a validation step that checks the judge itself.",
};

export default function EvaluationLayout({ children }: { children: React.ReactNode }) {
  return children;
}
