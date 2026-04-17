import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8100/:path*",
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.aliyuncs.com",
      },
    ],
  },
};

export default withSentryConfig(nextConfig, {
  silent: true,
  webpack: {
    treeshake: {
      removeDebugLogging: true,
    },
    automaticVercelMonitors: false,
  },
});
