"use client";

import { motion, useReducedMotion } from "framer-motion";

/**
 * Cross-route enter transition. `template.tsx` (unlike `layout.tsx`) remounts on
 * every navigation, so this replays as you move between pages.
 *
 * Opacity only, deliberately: a transform or filter on this wrapper would make
 * it the containing block for every `position: fixed` descendant, which would
 * break the nav, the ambient backdrop, and the grain overlay. Opacity creates a
 * stacking context but not a containing block, so fixed children stay anchored
 * to the viewport.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  const reduced = useReducedMotion();
  if (reduced) return <>{children}</>;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
