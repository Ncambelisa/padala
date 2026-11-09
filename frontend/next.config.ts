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

function apiInternalUrl() {
  // Render Blueprints can safely supply a private `host:port` reference, but
  // they cannot interpolate an `http://` prefix in YAML. The value is used
  // exclusively by Next.js on the server; browsers only call same-origin
  // `/api/v1` URLs and never receive this internal address.
  const explicit = process.env.API_INTERNAL_URL?.trim();
  if (explicit) return explicit.replace(/\/+$/, '');
  const hostPort = process.env.API_INTERNAL_HOSTPORT?.trim();
  if (hostPort) return `http://${hostPort}`;
  return 'http://127.0.0.1:8000';
}

const config: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    // Only this server-to-server address is configurable; no browser API secret exists.
    const api = apiInternalUrl();
    return [{ source: '/api/v1/:path*', destination: `${api}/api/v1/:path*` }];
  },
  async headers() {
    return [
      { source: '/:path*', headers: securityHeaders },
      // Receipt previews are validated uploads and remain private to the
      // household. This narrow exception allows the app's own preview frame.
      { source: '/api/v1/uploads/:uploadId/preview', headers: [{ key: 'X-Frame-Options', value: 'SAMEORIGIN' }] },
    ];
  },
};
export default config;
