import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const allowedOrigins = process.env.ALLOWED_DEV_ORIGIN
  ? process.env.ALLOWED_DEV_ORIGIN.split(",")
      .map((o) => o.trim())
      .filter(Boolean)
  : [];

const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  allowedDevOrigins: allowedOrigins,
  async rewrites() {
    const MINIO_ORIGIN = process.env.MINIO_ORIGIN || "http://127.0.0.1:9000";
    return [
      { source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` },
      { source: "/health", destination: `${BACKEND_ORIGIN}/health` },
      { source: "/outputs/:path*", destination: `${BACKEND_ORIGIN}/outputs/:path*` },
      { source: "/assets/:path*", destination: `${BACKEND_ORIGIN}/assets/:path*` },
      { source: "/storage/:path*", destination: `${MINIO_ORIGIN}/:path*` },
    ];
  },
  async redirects() {
    return [
      { source: "/characters/:path*", destination: "/library/characters/:path*", permanent: true },
      { source: "/voices", destination: "/library/voices", permanent: true },
      { source: "/music", destination: "/library/music", permanent: true },
      { source: "/manage", destination: "/library/characters", permanent: true },
      { source: "/library", destination: "/library/characters", permanent: false },
      { source: "/settings/trash", destination: "/library/trash", permanent: true },
      { source: "/settings", destination: "/settings/presets", permanent: false },
      { source: "/dev", destination: "/dev/sd-models", permanent: false },
      { source: "/scripts", destination: "/studio", permanent: true },
      { source: "/storyboards", destination: "/", permanent: true },
      { source: "/library/loras", destination: "/dev/sd-models", permanent: true },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG || "tomo-playground",
  project: process.env.SENTRY_PROJECT || "shorts-producer-frontend",
  silent: !process.env.CI,
  tunnelRoute: "/monitoring",
});
