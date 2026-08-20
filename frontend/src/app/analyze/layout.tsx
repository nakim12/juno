import type { Metadata } from "next";

// The page itself is a client component and can't export metadata.
export const metadata: Metadata = {
  title: "Analyze",
  description:
    "Load an MMM output and watch Juno interpret it — a grounded, cited, confidence-tagged report streamed live.",
};

export default function AnalyzeLayout({ children }: { children: React.ReactNode }) {
  return children;
}
