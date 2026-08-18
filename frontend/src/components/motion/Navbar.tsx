"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { LaurelWreath } from "@/components/motion/LaurelWreath";

/** Pill width at rest, in px. Mirrors Tailwind's max-w-2xl. */
const PILL_MAX = 672;
/** How far the pill floats below the viewport top, in px. Mirrors mt-3. */
const FLOAT_Y = 12;

const EASE = "cubic-bezier(0.22,1,0.36,1)";
const DUR = 420;

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [inset, setInset] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Direct, rAF-coalesced scroll read (updates once per frame).
    //
    // Thresholds are viewport-relative with hysteresis, and deliberately far
    // from 0: momentum scrolling has a long slow tail near the top, so a small
    // threshold makes the pill look like it "realizes" it's at the top a second
    // late. Reverting well before the top makes it feel immediate, and the wide
    // bar is the right treatment while you're still over the hero anyway.
    let raf = 0;
    const update = () => {
      raf = 0;
      const y = window.scrollY;
      const vh = window.innerHeight || 800;
      setScrolled((prev) => (prev ? y > vh * 0.2 : y > vh * 0.28));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  useEffect(() => {
    // The pill morph is expressed as transforms, which need a pixel distance.
    // Measured on resize only, never during the transition, so no per-frame
    // layout reads.
    const measure = () => {
      const w = wrapRef.current?.offsetWidth ?? 0;
      setInset(Math.max(0, (w - PILL_MAX) / 2));
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  // Inline rather than Tailwind classes: the values are interpolated, and
  // Tailwind's scanner can't see class names built at runtime.
  const slide = (dx: number) => ({
    transform: `translate3d(${dx}px,0,0)`,
    transition: `transform ${DUR}ms ${EASE}`,
  });

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-50 flex justify-center px-3 pt-3">
      <div
        ref={wrapRef}
        className="relative w-full max-w-6xl"
        style={{
          transform: `translate3d(0,${scrolled ? 0 : -FLOAT_Y}px,0)`,
          transition: `transform ${DUR}ms ${EASE}`,
        }}
      >
        {/*
          Decoration is a separate layer pinned at the pill's final geometry, so
          becoming a pill only fades it in — no width/padding/radius animation.
          Deliberately no backdrop-blur: it would sit over the animated ambient
          canvases and force a re-blur every frame the whole time it's visible.
          The near-opaque background reads the same for a fraction of the cost.
        */}
        <div
          aria-hidden
          className="absolute inset-y-0 rounded-full border border-border bg-background/95 shadow-xl shadow-black/40"
          style={{
            left: inset,
            right: inset,
            opacity: scrolled ? 1 : 0,
            transition: `opacity ${DUR}ms ${EASE}`,
          }}
        />
        <nav className="pointer-events-auto relative flex items-center justify-between px-6 py-3.5">
          <Link
            href="/"
            className="mono flex items-center gap-2 text-sm font-medium"
            style={slide(scrolled ? inset : 0)}
          >
            <LaurelWreath className="h-7 w-7 text-accent" />
            juno<span className="text-accent">.</span>
          </Link>
          <div
            className="mono flex items-center gap-5 text-xs sm:gap-7"
            style={slide(scrolled ? -inset : 0)}
          >
            <a
              href="#how"
              className="hidden text-muted-foreground transition-colors hover:text-foreground sm:inline"
            >
              how it works
            </a>
            <Link
              href="/evaluation"
              className="hidden text-muted-foreground transition-colors hover:text-foreground sm:inline"
            >
              evaluation
            </Link>
            <Link
              href="/analyze"
              className="rounded-md border border-border bg-muted/60 px-3 py-1.5 font-medium text-foreground transition-colors hover:border-accent"
            >
              try the demo →
            </Link>
          </div>
        </nav>
      </div>
    </div>
  );
}

export default Navbar;
