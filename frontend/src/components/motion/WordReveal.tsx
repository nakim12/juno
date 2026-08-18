"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";

export type WordRevealPart = { text: string; className?: string };

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.04 } },
};

// Only opacity + translate — both GPU-composited and cheap. (An animated CSS
// blur filter here tanks scroll performance: it forces a filter layer per word
// that the compositor must repaint every frame.)
const word: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
  },
};

/**
 * Reveals a heading word-by-word as it scrolls into view: each word rises and
 * un-blurs on a stagger. `parts` may be a plain string or styled segments (so a
 * gradient/highlighted phrase can share the same reveal). Renders plainly under
 * reduced-motion.
 */
export function WordReveal({
  parts,
  className = "",
}: {
  parts: string | WordRevealPart[];
  className?: string;
}) {
  const reduced = useReducedMotion();
  const segments: WordRevealPart[] =
    typeof parts === "string" ? [{ text: parts }] : parts;

  if (reduced) {
    return (
      <span className={className}>
        {segments.map((p, i) => (
          <span key={i} className={p.className}>
            {i > 0 ? " " : ""}
            {p.text}
          </span>
        ))}
      </span>
    );
  }

  const words: WordRevealPart[] = [];
  for (const seg of segments) {
    for (const w of seg.text.split(/\s+/).filter(Boolean)) {
      words.push({ text: w, className: seg.className });
    }
  }

  return (
    <motion.span
      className={className}
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-10% 0px" }}
    >
      {words.map((w, i) => (
        <motion.span
          key={i}
          variants={word}
          className={`inline-block ${w.className ?? ""}`}
        >
          {w.text}
          {i < words.length - 1 ? "\u00A0" : ""}
        </motion.span>
      ))}
    </motion.span>
  );
}

export default WordReveal;
