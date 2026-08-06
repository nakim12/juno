"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { LEAF_PATH, LEFT, RIGHT, STEMS } from "@/components/motion/LaurelWreath";

const SESSION_KEY = "juno_intro_seen";
// How long the emblem holds on screen before it fades away. The gold rule
// finishes at ~3.3s (delay 2.5s + 0.8s), so the fade begins right as it lands.
const HOLD_MS = 3300;
const HOLD_MS_REDUCED = 700;

function AnimatedLaurel({ reduced }: { reduced: boolean }) {
  // When motion is reduced we render the finished emblem with no drawing.
  const stemAnim = reduced
    ? { initial: { pathLength: 1 }, animate: { pathLength: 1 } }
    : { initial: { pathLength: 0 }, animate: { pathLength: 1 } };

  return (
    <svg
      viewBox="0 0 100 100"
      className="h-44 w-44 text-accent sm:h-56 sm:w-56"
      fill="none"
      aria-hidden
    >
      {STEMS.map((d, i) => (
        <motion.path
          key={`stem-${i}`}
          d={d}
          stroke="currentColor"
          strokeWidth={1.4}
          strokeLinecap="round"
          opacity={0.5}
          initial={stemAnim.initial}
          animate={stemAnim.animate}
          transition={{ duration: reduced ? 0 : 1.7, ease: "easeInOut" }}
        />
      ))}

      {/* Left and right sprigs grow symmetrically, base -> tip. */}
      {[LEFT, RIGHT].map((sprig, side) =>
        sprig.map((leaf, i) => (
          <g
            key={`leaf-${side}-${i}`}
            transform={`translate(${leaf.x.toFixed(1)} ${leaf.y.toFixed(1)}) rotate(${leaf.angle.toFixed(
              1,
            )}) scale(${leaf.scale.toFixed(2)})`}
          >
            <motion.path
              d={LEAF_PATH}
              fill="currentColor"
              initial={reduced ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                delay: reduced ? 0 : 0.5 + i * 0.16,
                duration: reduced ? 0 : 0.7,
                ease: [0.22, 1, 0.36, 1],
              }}
              style={{ transformBox: "fill-box", transformOrigin: "center" }}
            />
          </g>
        )),
      )}
    </svg>
  );
}

export function Intro() {
  const reduced = useReducedMotion() ?? false;
  // Start visible so the very first server-rendered paint is covered (no hero
  // flash). On already-seen sessions the effect removes it immediately.
  const [visible, setVisible] = useState(true);
  // When we dismiss because the intro was already seen this session, skip the
  // exit fade so there's no partial-draw flicker on reloads.
  const skipExit = useRef(false);

  useEffect(() => {
    if (sessionStorage.getItem(SESSION_KEY)) {
      skipExit.current = true;
      setVisible(false);
      return;
    }

    document.body.style.overflow = "hidden";
    const hold = reduced ? HOLD_MS_REDUCED : HOLD_MS;
    const t = window.setTimeout(() => {
      sessionStorage.setItem(SESSION_KEY, "1");
      setVisible(false);
    }, hold);

    return () => {
      window.clearTimeout(t);
      document.body.style.overflow = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AnimatePresence onExitComplete={() => (document.body.style.overflow = "")}>
      {visible && (
        <motion.div
          key="intro"
          className="fixed inset-0 z-[60] flex items-center justify-center overflow-hidden bg-background"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: skipExit.current ? 0 : 0.9, ease: "easeInOut" }}
        >
          {/* subtle glow behind the emblem */}
          <div className="hero-glow pointer-events-none absolute inset-0 -z-10" aria-hidden />

          <div className="flex flex-col items-center">
            <AnimatedLaurel reduced={reduced} />

            <motion.div
              initial={reduced ? { opacity: 1, y: 0 } : { opacity: 0, y: 10, filter: "blur(10px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ delay: reduced ? 0 : 1.9, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
              className="display mt-6 select-none text-center text-6xl font-semibold sm:text-7xl"
            >
              juno<span className="text-accent">.</span>
            </motion.div>

            {/* thin gold rule that draws outward under the wordmark */}
            <motion.div
              className="mt-5 h-px bg-gradient-to-r from-transparent via-accent to-transparent"
              initial={reduced ? { width: "8rem" } : { width: 0 }}
              animate={{ width: "8rem" }}
              transition={{ delay: reduced ? 0 : 2.5, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default Intro;
