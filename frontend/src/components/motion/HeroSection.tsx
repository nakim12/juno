"use client";

import Link from "next/link";
import { useRef } from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { LaurelWreath } from "@/components/motion/LaurelWreath";
import { Reveal } from "@/components/motion/Reveal";
import { DustMotes } from "@/components/motion/DustMotes";
import { ContourLines } from "@/components/motion/ContourLines";

export function HeroSection({ githubUrl }: { githubUrl: string }) {
  const ref = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });

  const scale = useTransform(scrollYProgress, [0, 1], [1, 0.9]);
  const y = useTransform(scrollYProgress, [0, 1], [0, -60]);
  const opacity = useTransform(scrollYProgress, [0, 0.75], [1, 0]);
  // Backdrop drifts up slowly and fades as you scroll — a slow parallax layer.
  const bgY = useTransform(scrollYProgress, [0, 1], [0, -80]);
  const bgScale = useTransform(scrollYProgress, [0, 1], [1, 1.08]);

  const contentStyle = reduced ? undefined : { scale, y, opacity };
  const bgStyle = reduced ? undefined : { y: bgY, scale: bgScale };
  const cueStyle = reduced ? undefined : { opacity };

  return (
    <section
      ref={ref}
      className="relative flex min-h-[100svh] flex-col overflow-hidden"
    >
      {/* Abstract backdrop — flowing gold contour lines */}
      <motion.div style={bgStyle} className="absolute inset-0 -z-10" aria-hidden>
        <ContourLines />
        {/* ambient breathing bloom */}
        {!reduced && (
          <motion.div
            className="absolute inset-0 mix-blend-screen"
            style={{
              background:
                "radial-gradient(38% 40% at 50% 42%, hsl(var(--accent) / 0.4) 0%, hsl(var(--accent) / 0.08) 45%, transparent 72%)",
            }}
            animate={{ opacity: [0.5, 0.9, 0.5], scale: [1, 1.06, 1] }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        {/* seat the centered content + blend the bottom into the page */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(65% 55% at 50% 50%, hsl(var(--background) / 0.68) 0%, hsl(var(--background) / 0.22) 48%, transparent 78%)",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-background/50" />
        <div className="grid-bg absolute inset-0 opacity-30" />
        <DustMotes />
      </motion.div>

      <motion.div
        style={contentStyle}
        className="relative mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center px-6 text-center"
      >
        {/* faint oversized laurel watermark keeps the Juno identity */}
        <LaurelWreath
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-1/2 -z-10 w-[min(34rem,82vw)] -translate-x-1/2 -translate-y-1/2 text-accent/[0.06]"
        />

        <Reveal>
          <LaurelWreath className="mx-auto mb-4 h-16 w-16 text-accent" />
        </Reveal>

        <Reveal delay={0.06}>
          <h1 className="display select-none text-[clamp(3.5rem,16vw,9.5rem)] font-semibold leading-[0.82]">
            <span className="wordmark-sheen">juno</span>
            <span className="text-accent">.</span>
          </h1>
        </Reveal>

        <Reveal delay={0.14}>
          <div className="mono mt-5 inline-flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1 text-[0.7rem] tracking-wider text-muted-foreground backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-3" />
            Marketing Mix Modeling · Agentic AI · LLM Evaluation
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <p className="mx-auto mt-4 max-w-2xl text-balance text-lg leading-relaxed text-muted-foreground sm:text-xl">
            Turn Marketing Mix Model outputs into{" "}
            <span className="text-foreground">decisions you can trust</span> — grounded,
            cited, and measurably evaluated.
          </p>
        </Reveal>

        <Reveal delay={0.28}>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/analyze"
              className="rounded-xl bg-gradient-to-br from-accent to-accent-2 px-6 py-3 text-sm font-semibold text-background shadow-lg shadow-accent/25 transition hover:opacity-90"
            >
              Try the live demo →
            </Link>
            <a
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
              className="mono rounded-xl border border-border bg-background/40 px-6 py-3 text-sm font-medium backdrop-blur-sm transition hover:border-accent"
            >
              View the code
            </a>
          </div>
        </Reveal>
      </motion.div>

      {/* Scroll cue */}
      <motion.a
        href="#showcase"
        style={cueStyle}
        className="mono group mx-auto mb-8 flex flex-col items-center gap-2 text-[0.7rem] text-muted-foreground transition hover:text-foreground"
      >
        <span>scroll</span>
        <span className="flex h-9 w-5 items-start justify-center rounded-full border border-border p-1">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" />
        </span>
      </motion.a>
    </section>
  );
}

export default HeroSection;
