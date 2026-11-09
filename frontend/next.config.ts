import type { NextConfig } from 'next';

const securityHeaders = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'no-referrer' },
  { key: 'Permissions-Policy', value: 'camera=(self), microphone=(), geolocation=(), browsing-topics=()' },
  { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
  { key: 'Cross-Origin-Resource-Policy', value: 'same-origin' },
  { key: 'X-Permitted-Cross-Domain-Policies', value: 'none' },
  ...(process.env.NODE_ENV === 'production'
    ? [{ key: 'Strict-Transport-Security', value: 'max-age=31536000' }]
    : []),
];

const config: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    // Only this server-to-server address is configurable; no browser API secret exists.
    const api = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
    return [{ source: '/api/v1/:path*', destination: `${api}/api/v1/:path*` }];
  },
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },
};
export default config;
