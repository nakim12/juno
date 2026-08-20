import type { Metadata, Viewport } from "next";
import { Fraunces, Inter, JetBrains_Mono } from "next/font/google";
import { ScrollProgress } from "@/components/motion/ScrollProgress";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  axes: ["opsz", "SOFT"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const DESCRIPTION =
  "An agentic AI copilot that turns Marketing Mix Model outputs into trustworthy, grounded business decisions — and ships with an evaluation framework that measures whether the advice can be trusted.";

// Absolute URLs are required for social cards. Vercel exposes the deploy host
// at build time; fall back to localhost so previews resolve in development.
const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Juno — MMM Copilot",
    template: "%s · Juno",
  },
  description: DESCRIPTION,
  applicationName: "Juno",
  openGraph: {
    type: "website",
    siteName: "Juno",
    title: "Juno — MMM Copilot",
    description: DESCRIPTION,
    url: SITE_URL,
  },
  twitter: {
    card: "summary_large_image",
    title: "Juno — MMM Copilot",
    description: DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: "#0A1128",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${fraunces.variable} ${jetbrainsMono.variable}`}
    >
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <div className="grain-overlay" aria-hidden />
        <ScrollProgress />
        {children}
      </body>
    </html>
  );
}
