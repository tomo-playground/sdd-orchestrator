import type { NextConfig } from "next";

const allowedOrigins = process.env.ALLOWED_DEV_ORIGIN
  ? [process.env.ALLOWED_DEV_ORIGIN]
  : [];

const nextConfig: NextConfig = {
  allowedDevOrigins: allowedOrigins,
};

export default nextConfig;
