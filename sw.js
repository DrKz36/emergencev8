const CACHE_NAME = 'emergence-shell-v1';
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
  '/src/frontend/styles/themes/dark.css',
  '/src/frontend/styles/themes/light.css',
  '/src/frontend/styles/pwa.css',
  '/assets/emergence_logo_icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
      .catch((error) => {
        console.warn('[SW] Install failed', error);
      })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
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

  if (isSameOrigin && SHELL_ASSETS.includes(url.pathname)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        });
      })
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (
          response &&
          response.status === 200 &&
          isSameOrigin &&
          response.type === 'basic'
        ) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
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
