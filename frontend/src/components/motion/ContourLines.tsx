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

    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let raf = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
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

    let t = 0;
    const render = () => {
      t += 0.016;
      ctx.clearRect(0, 0, width, height);
      for (let i = 0; i < lines; i++) drawLine(i, t);
      raf = requestAnimationFrame(render);
    };

    resize();
    if (reduced) {
      for (let i = 0; i < lines; i++) drawLine(i, 0);
    } else {
      render();
    }
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
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
