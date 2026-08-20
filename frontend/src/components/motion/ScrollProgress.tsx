"use client";

import { motion, useReducedMotion, useScroll, useSpring } from "framer-motion";

/**
 * Hairline gold reading-progress bar pinned to the top of the viewport.
 *
 * Driven purely by `transform: scaleX`, which the compositor can animate without
 * touching layout — important because this updates on every scroll frame and
 * sits above canvas-heavy pages.
 */
export function ScrollProgress() {
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 320,
    damping: 40,
    restDelta: 0.001,
  });

  return (
    <motion.div
      aria-hidden
      className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-[2px] origin-left bg-gradient-to-r from-accent via-accent-3 to-accent-2"
      style={{ scaleX: reduced ? scrollYProgress : scaleX }}
    />
  );
}

export default ScrollProgress;
