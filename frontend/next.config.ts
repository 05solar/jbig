// Next.js 빌드 설정 파일
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    useTypeScriptCli: false,
  },
};

export default nextConfig;
