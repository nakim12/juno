import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Juno — MMM Copilot",
  description:
    "An agentic AI copilot that turns Marketing Mix Model outputs into trustworthy, grounded business decisions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
