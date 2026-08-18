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
export function DustMotes({ count = 30 }: { count?: number }) {
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
    // The motes are soft gradient sprites with no hard edges, so backing beyond
    // ~1.25x is spent clearing and compositing pixels nobody can distinguish.
    let dpr = Math.min(window.devicePixelRatio || 1, 1.25);
    let motes: Mote[] = [];
    let raf = 0;

    // Pre-rendered soft glow sprite: drawing this scaled is far cheaper than a
    // per-particle ctx.shadowBlur (which re-blurs every fill, every frame).
    const SPRITE = 24;
    const sprite = document.createElement("canvas");
    sprite.width = sprite.height = SPRITE;
    const sctx = sprite.getContext("2d");
    if (sctx) {
      const g = sctx.createRadialGradient(
        SPRITE / 2, SPRITE / 2, 0, SPRITE / 2, SPRITE / 2, SPRITE / 2,
      );
      g.addColorStop(0, "rgba(214, 168, 84, 0.95)");
      g.addColorStop(1, "rgba(214, 168, 84, 0)");
      sctx.fillStyle = g;
      sctx.fillRect(0, 0, SPRITE, SPRITE);
    }

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
      dpr = Math.min(window.devicePixelRatio || 1, 1.25);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (motes.length === 0) seed();
    };

    // Ambient dust doesn't need 60fps; cap to ~30 and pause when off-screen.
    const FRAME_MS = 1000 / 30;
    let last = 0;
    let visible = true;
    let t = 0;

    const render = (now: number) => {
      raf = requestAnimationFrame(render);
      if (!visible) return;
      if (now - last < FRAME_MS) return;
      last = now;
      t += 0.032;
      ctx.clearRect(0, 0, width, height);
      for (const m of motes) {
        m.y -= m.speed;
        m.x += m.drift + Math.sin(t * 0.5 + m.phase) * 0.15;
        if (m.y < -4) {
          m.y = height + 4;
          m.x = Math.random() * width;
        }
        const alpha = m.baseAlpha * (0.55 + 0.45 * Math.sin(t * m.twinkle + m.phase));
        const d = m.r * 6;
        ctx.globalAlpha = Math.max(0, alpha);
        ctx.drawImage(sprite, m.x - d / 2, m.y - d / 2, d, d);
      }
      ctx.globalAlpha = 1;
    };

    resize();
    const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting), {
      threshold: 0,
    });
    io.observe(canvas);
    raf = requestAnimationFrame(render);
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      io.disconnect();
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
