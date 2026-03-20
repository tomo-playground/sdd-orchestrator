import type { NextConfig } from "next";

const allowedOrigins = process.env.ALLOWED_DEV_ORIGIN
  ? [process.env.ALLOWED_DEV_ORIGIN]
  : [];

const nextConfig: NextConfig = {
  allowedDevOrigins: allowedOrigins,
  async redirects() {
    return [
      { source: "/characters/:path*", destination: "/library/characters/:path*", permanent: true },
      { source: "/voices", destination: "/library/voices", permanent: true },
      { source: "/music", destination: "/library/music", permanent: true },
      { source: "/manage", destination: "/library/characters", permanent: true },
      { source: "/library", destination: "/library/characters", permanent: false },
      { source: "/settings", destination: "/settings/presets", permanent: false },
      { source: "/dev", destination: "/dev/sd-models", permanent: false },
    ];
  },
};

export default nextConfig;
