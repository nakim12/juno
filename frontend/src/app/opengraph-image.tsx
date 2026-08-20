import { ImageResponse } from "next/og";
import { BRAND, laurelDataUri } from "@/lib/laurel-mark";

export const alt = "Juno — turn Marketing Mix Model outputs into decisions you can trust";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/**
 * Social preview card. Deliberately uses only system fonts: fetching Fraunces
 * at build time would make image generation depend on network access from CI.
 */
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: BRAND.background,
          backgroundImage: `radial-gradient(60% 60% at 50% 38%, ${BRAND.accent}22 0%, transparent 70%)`,
          padding: 64,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          width={152}
          height={152}
          alt=""
          src={laurelDataUri({ stemWidth: 2, leafScale: 1.15 })}
        />

        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            fontSize: 132,
            fontWeight: 700,
            color: BRAND.foreground,
            letterSpacing: -4,
            marginTop: 8,
          }}
        >
          juno
          <span style={{ color: BRAND.accent }}>.</span>
        </div>

        <div
          style={{
            fontSize: 30,
            color: BRAND.muted,
            textAlign: "center",
            marginTop: 18,
            maxWidth: 880,
            lineHeight: 1.35,
          }}
        >
          Turn Marketing Mix Model outputs into decisions you can trust — grounded, cited,
          and measurably evaluated.
        </div>

        <div
          style={{
            display: "flex",
            gap: 28,
            marginTop: 40,
            fontSize: 22,
            color: BRAND.accent2,
          }}
        >
          <span>100 benchmark cases</span>
          <span style={{ color: BRAND.muted }}>·</span>
          <span>87.5% ranking accuracy</span>
          <span style={{ color: BRAND.muted }}>·</span>
          <span>0.90 groundedness</span>
        </div>
      </div>
    ),
    size
  );
}
