"use client";

import { useEffect, useRef } from "react";

/**
 * Slow, flowing gold contour lines — a calm abstract backdrop.
 * Canvas-based; renders a single static frame for reduced-motion users.
 */
export function ContourLines({ lines = 16 }: { lines?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Render at 1x regardless of device pixel ratio. These are slow, soft,
    // very-low-alpha curves, so retina backing gains nothing visible while
    // costing 4x the fill rate on a full-viewport canvas.
    const DPR = 1;

    let width = 0;
    let height = 0;
    let raf = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.floor(width * DPR);
      canvas.height = Math.floor(height * DPR);
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    };

    const drawLine = (i: number, t: number) => {
      // Each line has its own vertical band, amplitude, wavelength and phase.
      const p = i / (lines - 1);
      const baseY = height * (0.12 + p * 0.82);
      const amp = height * (0.03 + 0.05 * Math.sin(p * Math.PI));
      const wavelength = width * (0.6 + 0.5 * ((i % 3) / 2));
      const speed = 0.15 + (i % 4) * 0.04;
      const phase = i * 0.7 + t * speed;

      // Fade lines toward the top so the wordmark area (bottom) stays calm-but-present.
      const alpha = 0.05 + 0.09 * Math.sin(p * Math.PI);

      ctx.beginPath();
      const step = 14;
      for (let x = -step; x <= width + step; x += step) {
        const y =
          baseY +
          amp * Math.sin((x / wavelength) * Math.PI * 2 + phase) +
          amp * 0.4 * Math.sin((x / (wavelength * 0.5)) * Math.PI * 2 - phase * 1.3);
        if (x === -step) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = `rgba(214, 168, 84, ${alpha.toFixed(3)})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    };

    // A calm background doesn't need 60fps; cap to ~24 and pause off-screen so
    // it doesn't compete with the compositor while scrolling elsewhere.
    const FPS = 24;
    const FRAME_MS = 1000 / FPS;
    let last = 0;
    let visible = true;
    let t = 0;

    const render = (now: number) => {
      raf = requestAnimationFrame(render);
      if (!visible) return;
      if (now - last < FRAME_MS) return;
      last = now;
      t += 0.04;
      ctx.clearRect(0, 0, width, height);
      for (let i = 0; i < lines; i++) drawLine(i, t);
    };

    resize();
    let io: IntersectionObserver | null = null;
    if (reduced) {
      for (let i = 0; i < lines; i++) drawLine(i, 0);
    } else {
      io = new IntersectionObserver(([e]) => (visible = e.isIntersecting), {
        threshold: 0,
      });
      io.observe(canvas);
      raf = requestAnimationFrame(render);
    }
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      io?.disconnect();
    };
  }, [lines]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
}

export default ContourLines;
