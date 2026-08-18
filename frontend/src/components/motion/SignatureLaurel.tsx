"use client";

import { useEffect, useRef } from "react";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import { LaurelWreath } from "@/components/motion/LaurelWreath";

/**
 * The Juno crest as a living emblem: it breathes on a slow loop and subtly
 * tilts toward the cursor (a 3D parallax "gaze"). Falls back to a static wreath
 * when the user prefers reduced motion.
 */
export function SignatureLaurel({
  className = "",
  wrapperClassName = "",
}: {
  className?: string;
  wrapperClassName?: string;
}) {
  const reduced = useReducedMotion();

  // Pointer position normalized to [-1, 1] from the viewport center.
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const sx = useSpring(px, { stiffness: 120, damping: 18, mass: 0.4 });
  const sy = useSpring(py, { stiffness: 120, damping: 18, mass: 0.4 });

  const rotateY = useTransform(sx, [-1, 1], [-16, 16]);
  const rotateX = useTransform(sy, [-1, 1], [14, -14]);
  const x = useTransform(sx, [-1, 1], [-6, 6]);
  const y = useTransform(sy, [-1, 1], [-6, 6]);

  const wrapRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (reduced) return;
    const el = wrapRef.current;

    // Only track the cursor while the emblem is actually on screen, so no
    // spring work happens once the hero is scrolled away.
    let visible = true;
    const io = el
      ? new IntersectionObserver(([e]) => (visible = e.isIntersecting), {
          threshold: 0,
        })
      : null;
    if (io && el) io.observe(el);

    // Coalesce pointer updates to one per animation frame.
    let raf = 0;
    let nx = 0;
    let ny = 0;
    function onMove(e: PointerEvent) {
      if (!visible) return;
      nx = (e.clientX / window.innerWidth) * 2 - 1;
      ny = (e.clientY / window.innerHeight) * 2 - 1;
      if (!raf) {
        raf = requestAnimationFrame(() => {
          raf = 0;
          px.set(nx);
          py.set(ny);
        });
      }
    }
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (raf) cancelAnimationFrame(raf);
      io?.disconnect();
    };
  }, [px, py, reduced]);

  if (reduced) {
    return (
      <span className={wrapperClassName}>
        <LaurelWreath className={className} />
      </span>
    );
  }

  return (
    <span
      ref={wrapRef}
      className={`inline-block ${wrapperClassName}`}
      style={{ perspective: 700 }}
    >
      <motion.span
        className="inline-block"
        style={{ rotateX, rotateY, x, y, transformStyle: "preserve-3d" }}
      >
        <motion.span
          className="inline-block"
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        >
          <LaurelWreath className={className} />
        </motion.span>
      </motion.span>
    </span>
  );
}

export default SignatureLaurel;
