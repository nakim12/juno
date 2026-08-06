"use client";

import { useEffect, useRef } from "react";

type Mote = {
  x: number;
  y: number;
  r: number;
  drift: number;
  speed: number;
  phase: number;
  twinkle: number;
  baseAlpha: number;
};

/**
 * Ambient gold dust drifting slowly upward through the hero's dark space.
 * Canvas-based for cheapness; disabled entirely for reduced-motion users.
 */
export function DustMotes({ count = 42 }: { count?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let motes: Mote[] = [];
    let raf = 0;

    const seed = () => {
      motes = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        r: 0.6 + Math.random() * 1.8,
        drift: (Math.random() - 0.5) * 0.25,
        speed: 0.12 + Math.random() * 0.4,
        phase: Math.random() * Math.PI * 2,
        twinkle: 0.6 + Math.random() * 1.6,
        baseAlpha: 0.15 + Math.random() * 0.4,
      }));
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (motes.length === 0) seed();
    };

    let t = 0;
    const render = () => {
      t += 0.016;
      ctx.clearRect(0, 0, width, height);
      for (const m of motes) {
        m.y -= m.speed;
        m.x += m.drift + Math.sin(t * 0.5 + m.phase) * 0.15;
        if (m.y < -4) {
          m.y = height + 4;
          m.x = Math.random() * width;
        }
        const alpha = m.baseAlpha * (0.55 + 0.45 * Math.sin(t * m.twinkle + m.phase));
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(214, 168, 84, ${alpha.toFixed(3)})`;
        ctx.shadowBlur = 6;
        ctx.shadowColor = "rgba(214, 168, 84, 0.5)";
        ctx.fill();
      }
      raf = requestAnimationFrame(render);
    };

    resize();
    render();
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, [count]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
}

export default DustMotes;
