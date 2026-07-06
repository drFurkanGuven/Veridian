import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  transpilePackages: ['@veridian/shared-types'],
  reactStrictMode: true,
  output: 'standalone',
};

export default nextConfig;
