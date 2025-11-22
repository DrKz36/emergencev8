const params = new URL(self.location.href).searchParams;
const CACHE_VERSION = params.get('v') || 'dev';
const SHELL_CACHE = `emergence-shell-${CACHE_VERSION}`;
const RUNTIME_CACHE = `emergence-runtime-${CACHE_VERSION}`;
const SHELL_ASSETS = [
  '/',
  '/index.html',
  '/src/frontend/main.js',
  '/src/frontend/core/app.js',
  '/src/frontend/core/state-manager.js',
  '/src/frontend/core/event-bus.js',
  '/src/frontend/shared/constants.js',
  '/src/frontend/shared/api-client.js',
  '/src/frontend/styles/core/reset.css',
  '/src/frontend/styles/core/_variables.css',
  '/src/frontend/styles/main-styles.css',
  '/src/frontend/styles/components/rag-power-button.css',
  '/src/frontend/styles/themes/dark.css',
  '/src/frontend/styles/themes/light.css',
  '/src/frontend/styles/pwa.css',
  '/assets/emergence_logo_icon.png'
];
const SHELL_ASSET_SET = new Set(SHELL_ASSETS);

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
      .catch((error) => {
        console.warn('[SW] Install failed', error);
      })
  );
});

self.addEventListener('activate', (event) => {
  const allowedCaches = new Set([SHELL_CACHE, RUNTIME_CACHE]);
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => !allowedCaches.has(key))
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
      .catch((error) => {
        console.warn('[SW] Activate cleanup failed', error);
      })
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);
  const isSameOrigin = url.origin === self.location.origin;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/index.html'))
    );
    return;
  }

  if (isSameOrigin && SHELL_ASSET_SET.has(url.pathname)) {
    event.respondWith(
      caches.open(SHELL_CACHE).then(async (cache) => {
        const cached = await cache.match(request);
        if (cached) return cached;
        const response = await fetch(request);
        if (response && response.status === 200) {
          cache.put(request, response.clone()).catch(() => {});
        }
        return response;
      })
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.status === 200 && isSameOrigin && response.type === 'basic') {
          const clone = response.clone();
          caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, clone)).catch(() => {});
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
