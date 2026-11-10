import type { NextConfig } from "next";

// The site is plain static files (the `out` folder), so it can be hosted free
// on GitHub Pages or any web host. If it lives under a sub-path such as
// https://<you>.github.io/<repo>/, set NEXT_PUBLIC_BASE_PATH=/<repo> when building.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  // Strict Mode mounts every component twice in `npm run dev`. The WebGL gallery can't
  // get its drawing surface back after the first unmount, so it showed a blank box in dev.
  reactStrictMode: false,
  basePath,
  trailingSlash: true,
  images: { unoptimized: true },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
