import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const isDev = process.env.NODE_ENV === "development";

    return [
      {
        source: "/api/:path*",
        destination: isDev ? "http://backend:8000/api/:path*" : "/api/:path*",
      },
    ];
  },
};

export default nextConfig;
