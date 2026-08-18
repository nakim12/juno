"use client";

import Link from "next/link";
import { LaurelWreath } from "@/components/motion/LaurelWreath";

/**
 * Shared top navigation for the inner pages (/analyze, /evaluation) so the whole
 * product feels like one world rather than three separate apps. The landing page
 * keeps its own scroll-pill Navbar; this is the calmer, sticky glass bar.
 */
export function InnerNav({ active }: { active?: "analyze" | "evaluation" }) {
  const linkBase = "transition hover:text-foreground";
  return (
    <nav className="sticky top-0 z-40 border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="mono flex items-center gap-2 text-sm font-medium">
          <LaurelWreath className="h-7 w-7 text-accent" />
          juno<span className="text-accent">.</span>
        </Link>
        <div className="mono flex items-center gap-6 text-xs">
          <Link href="/" className={`text-muted-foreground ${linkBase}`}>
            home
          </Link>
          <Link
            href="/evaluation"
            className={
              active === "evaluation"
                ? "text-foreground"
                : `text-muted-foreground ${linkBase}`
            }
          >
            evaluation
          </Link>
          <Link
            href="/analyze"
            className={`rounded-md border px-3 py-1.5 font-medium text-foreground transition hover:border-accent ${
              active === "analyze" ? "border-accent bg-muted" : "border-border bg-muted/60"
            }`}
          >
            try the demo →
          </Link>
        </div>
      </div>
    </nav>
  );
}

export default InnerNav;
