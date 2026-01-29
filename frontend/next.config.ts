import type { NextConfig } from "next";

const allowedOrigins = process.env.ALLOWED_DEV_ORIGIN
  ? [process.env.ALLOWED_DEV_ORIGIN]
  : [];

const nextConfig: NextConfig = {
  allowedDevOrigins: allowedOrigins,
  async rewrites() {
    return [
      {
        source: "/outputs/:path*",
        destination: "http://127.0.0.1:8000/outputs/:path*",
      },
      {
        source: "/assets/:path*",
        destination: "http://127.0.0.1:8000/assets/:path*",
      },
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
