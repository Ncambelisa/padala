import type { Metadata, Viewport } from 'next';
import './globals.css';
import './review-status.css';
export const metadata: Metadata = {
  title: 'Padala — care, accounted for',
  description: 'Shared remittance allocations and receipt records for your household.',
  manifest: '/manifest.webmanifest',
  icons: { icon: '/icon.svg', apple: '/icon-192.png' },
  appleWebApp: { capable: true, title: 'Padala', statusBarStyle: 'default' },
};
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#124e49' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
