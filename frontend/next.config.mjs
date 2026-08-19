/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // `next build` and `next dev` share .next by default, so building while the
  // dev server runs overwrites its chunks and leaves it serving 404s for
  // main-app.js — the page then renders but never hydrates. Set NEXT_DIST_DIR
  // to give a production build its own directory (see the build:prod script).
  distDir: process.env.NEXT_DIST_DIR || ".next",
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
