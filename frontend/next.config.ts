import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // Disable static optimization for pages with dynamic routes
  // They will be handled client-side via SPA fallback
};

export default nextConfig;
