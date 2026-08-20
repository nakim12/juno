import { ImageResponse } from "next/og";
import { BRAND } from "@/lib/laurel-mark";

export const size = { width: 64, height: 64 };
export const contentType = "image/png";

/**
 * Favicon. Deliberately the wordmark's letterform rather than the laurel crest:
 * the crest's twelve separate leaves turn to mush below ~48px, while a single
 * glyph stays legible at 16px. The full crest still fronts the OG card, where
 * there's resolution to carry it.
 */
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: BRAND.background,
          borderRadius: 14,
        }}
      >
        <div
          style={{
            display: "flex",
            fontSize: 54,
            fontWeight: 700,
            color: BRAND.accent,
            // The descender pulls the glyph's visual mass low; nudge it up so it
            // sits optically centred rather than metrically centred.
            marginTop: -8,
          }}
        >
          j
        </div>
      </div>
    ),
    size
  );
}
