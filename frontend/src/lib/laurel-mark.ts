import { LEAF_PATH, LEFT, RIGHT, STEMS } from "@/components/motion/LaurelWreath";

/**
 * The laurel crest as a standalone SVG string, for contexts that can't render
 * React components — favicons and OG images generated via `next/og`, which
 * rasterizes through Satori and handles `<img>` data URIs far more reliably
 * than inline SVG elements.
 *
 * Geometry is imported from the LaurelWreath component rather than duplicated,
 * so the icon can never drift from the logo shown in the UI.
 */
export function laurelSvg({
  color = "#D4A574",
  stemWidth = 1.4,
  stemOpacity = 0.45,
  inset = 0,
  leafScale = 1,
}: {
  color?: string;
  /** Thicker stems survive rasterization at favicon sizes. */
  stemWidth?: number;
  stemOpacity?: number;
  /** Crops the viewBox to make the mark fill more of the frame. */
  inset?: number;
  /** Fattens the leaves; small raster sizes need far more mass to read. */
  leafScale?: number;
} = {}): string {
  const stems = STEMS.map(
    (d) =>
      `<path d="${d}" stroke="${color}" stroke-width="${stemWidth}" fill="none" opacity="${stemOpacity}"/>`
  ).join("");

  const leafShapes = [...LEFT, ...RIGHT]
    .map(
      (l) =>
        `<path d="${LEAF_PATH}" fill="${color}" transform="translate(${l.x.toFixed(
          1
        )} ${l.y.toFixed(1)}) rotate(${l.angle.toFixed(1)}) scale(${(
          l.scale * leafScale
        ).toFixed(2)})"/>`
    )
    .join("");

  const box = `${inset} ${inset} ${100 - inset * 2} ${100 - inset * 2}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${box}">${stems}${leafShapes}</svg>`;
}

/** Same mark as a data URI. Uses percent-encoding so it works on any runtime. */
export function laurelDataUri(opts?: Parameters<typeof laurelSvg>[0]): string {
  return `data:image/svg+xml;utf8,${encodeURIComponent(laurelSvg(opts))}`;
}

/** Brand colors, duplicated from globals.css for image generation. */
export const BRAND = {
  background: "#0A1128",
  accent: "#D4A574",
  accent2: "#C99B4A",
  foreground: "#F5F1E8",
  muted: "#8A93AD",
} as const;
