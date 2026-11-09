import { connection } from 'next/server';
import PadalaApp from '@/components/PadalaApp';

// Production CSP uses a fresh nonce per request, which requires dynamic rendering.
export default async function Page() {
  await connection();
  return <PadalaApp />;
}
