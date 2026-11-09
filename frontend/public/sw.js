/* Network-only private app. Do not cache API responses, receipts, or household pages. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => new Response(
      '<!doctype html><meta name="viewport" content="width=device-width"><title>Padala offline</title><main style="font-family:system-ui;padding:32px;max-width:500px;margin:auto"><h1>You are offline.</h1><p>Reconnect to view your household records. Padala does not store private receipts in an offline cache.</p><button onclick="location.reload()">Try again</button></main>',
      { headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control':'no-store' } }
    )));
  }
});
