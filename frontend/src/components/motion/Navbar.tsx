"use client";

import Link from "next/link";
import { useState } from "react";
import { useMotionValueEvent, useScroll } from "framer-motion";
import { LaurelWreath } from "@/components/motion/LaurelWreath";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, "change", (v) => setScrolled(v > 40));

  return (
    <div className="fixed inset-x-0 top-0 z-50 flex justify-center px-3">
      <nav
        className={`flex w-full items-center justify-between transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
          scrolled
            ? "mt-3 max-w-2xl rounded-full border border-border bg-background/75 px-5 py-2.5 shadow-xl shadow-black/40 backdrop-blur-xl"
            : "mt-0 max-w-6xl rounded-none border border-transparent bg-transparent px-6 py-4"
        }`}
      >
        <Link href="/" className="mono flex items-center gap-2 text-sm font-medium">
          <LaurelWreath className="h-7 w-7 text-accent" />
          juno<span className="text-accent">.</span>
        </Link>
        <div className="mono flex items-center gap-5 text-xs sm:gap-7">
          <a
            href="#how"
            className="hidden text-muted-foreground transition hover:text-foreground sm:inline"
          >
            how it works
          </a>
          <Link
            href="/evaluation"
            className="hidden text-muted-foreground transition hover:text-foreground sm:inline"
          >
            evaluation
          </Link>
          <Link
            href="/analyze"
            className={`rounded-md border font-medium text-foreground transition hover:border-accent ${
              scrolled ? "border-border bg-muted px-3 py-1.5" : "border-border bg-muted/60 px-3 py-1.5"
            }`}
          >
            try the demo →
          </Link>
        </div>
      </nav>
    </div>
  );
}

export default Navbar;
