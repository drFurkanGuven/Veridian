import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  transpilePackages: ['@veridian/shared-types'],
  reactStrictMode: true,
  output: 'standalone',
  async redirects() {
    return [
      {
        source: '/favicon.ico',
        destination: '/favicon.svg',
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
