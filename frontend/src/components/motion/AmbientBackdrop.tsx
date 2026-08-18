"use client";

import { ContourLines } from "@/components/motion/ContourLines";

/**
 * A page-wide ambient layer that lives behind all content.
 * Two slow-drifting gold glows (dialed-style clouds) plus the faint
 * flowing contour lines (romus-style) keep the whole page gently in motion.
 * Fixed to the viewport so movement is present through every section.
 */
export function AmbientBackdrop() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-20 overflow-hidden"
    >
      <div className="ambient-blob ambient-blob--1" />
      <div className="ambient-blob ambient-blob--2" />
      <div className="absolute inset-0 opacity-60">
        <ContourLines lines={14} />
      </div>
    </div>
  );
}

export default AmbientBackdrop;
